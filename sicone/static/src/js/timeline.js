/** @odoo-module alias=sicone.timeline **/
(function () {
    "use strict";

    // ── Colores por instrumento ──────────────────────────────────────────
    var COLORES = {
        'cdt':               '#378ADD',   // azul
        'fondo_liquidez':    '#1D9E75',   // verde
        'fondo_corto_plazo': '#E67E22',   // naranja
        'cuenta_remunerada': '#95A5A6',   // gris
    };
    var NOMBRES = {
        'cdt':               'CDT',
        'fondo_liquidez':    'Fondo de Liquidez',
        'fondo_corto_plazo': 'Fondo Corto Plazo',
        'cuenta_remunerada': 'Cuenta Remunerada',
    };

    function fmt(v) {
        var a = Math.abs(v);
        var s = a >= 1e9 ? (a / 1e9).toFixed(1) + "B"
              : a >= 1e6 ? Math.round(a / 1e6) + "M"
              : a >= 1e3 ? Math.round(a / 1e3) + "K"
              : a.toFixed(0);
        return (v < 0 ? "-" : "") + "$" + s;
    }

    function fmtFecha(iso) {
        // iso: "2026-06-08" → "08/06/26"
        var p = iso.split('-');
        return p[2] + '/' + p[1] + '/' + p[0].slice(2);
    }

    function renderTimeline(container, inversiones) {
        // ── Calcular rango de fechas ─────────────────────────────────
        var hoy = new Date();
        hoy.setHours(0, 0, 0, 0);

        var fechaMax = new Date(hoy);
        inversiones.forEach(function(inv) {
            var fv = new Date(inv.fecha_vencimiento);
            if (fv > fechaMax) fechaMax = fv;
        });

        // Agregar 7 días de margen al final
        fechaMax.setDate(fechaMax.getDate() + 7);
        var totalDias = Math.ceil((fechaMax - hoy) / 86400000);

        // ── Monto máximo para escala de grosor ───────────────────────
        var montoMax = Math.max.apply(null, inversiones.map(function(i){ return i.monto; }));

        // ── Construir SVG ────────────────────────────────────────────
        var padLeft  = 180;  // espacio para nombres
        var padRight = 20;
        var padTop   = 40;   // espacio para eje de fechas
        var padBot   = 20;
        var rowH     = 60;   // altura base por fila
        var svgW     = container.clientWidth || 800;
        var chartW   = svgW - padLeft - padRight;
        var svgH     = padTop + inversiones.length * rowH + padBot;

        // Escala: días → píxeles
        function px(dias) { return (dias / totalDias) * chartW; }

        // Marcar meses en el eje X
        var meses = ['Ene','Feb','Mar','Abr','May','Jun',
                     'Jul','Ago','Sep','Oct','Nov','Dic'];
        var ticksHtml = '';
        var cur = new Date(hoy);
        cur.setDate(1); // ir al día 1 del mes actual
        while (cur <= fechaMax) {
            var diasDesdeHoy = Math.ceil((cur - hoy) / 86400000);
            if (diasDesdeHoy >= 0) {
                var xTick = padLeft + px(diasDesdeHoy);
                ticksHtml += '<line x1="' + xTick + '" y1="' + (padTop - 5) +
                    '" x2="' + xTick + '" y2="' + (svgH - padBot) +
                    '" stroke="#eee" stroke-width="1"/>';
                ticksHtml += '<text x="' + (xTick + 3) + '" y="' + (padTop - 8) +
                    '" font-size="10" fill="#999">' +
                    meses[cur.getMonth()] + ' ' + String(cur.getFullYear()).slice(2) +
                    '</text>';
            }
            cur.setMonth(cur.getMonth() + 1);
        }

        // Línea "hoy"
        var xHoy = padLeft;
        ticksHtml += '<line x1="' + xHoy + '" y1="' + (padTop - 5) +
            '" x2="' + xHoy + '" y2="' + (svgH - padBot) +
            '" stroke="#E74C3C" stroke-width="1.5" stroke-dasharray="4,3"/>';
        ticksHtml += '<text x="' + (xHoy + 3) + '" y="14" font-size="10" fill="#E74C3C" font-weight="bold">HOY</text>';

        // Barras por inversión
        var barrasHtml = '';
        inversiones.forEach(function(inv, idx) {
            var yCenter = padTop + idx * rowH + rowH / 2;

            // Grosor proporcional al monto (min 8px, max 36px)
            var grosor = 8 + (inv.monto / montoMax) * 28;

            // Días desde hoy hasta inicio y vencimiento
            var fi = new Date(inv.fecha_inicio);
            var fv = new Date(inv.fecha_vencimiento);
            fi.setHours(0,0,0,0);
            fv.setHours(0,0,0,0);
            var diasInicio = Math.max(0, Math.ceil((fi - hoy) / 86400000));
            var diasFin    = Math.ceil((fv - hoy) / 86400000);

            var xIni  = padLeft + px(diasInicio);
            var xFin  = padLeft + px(diasFin);
            var barW  = Math.max(xFin - xIni, 4);
            var color = COLORES[inv.instrumento] || '#378ADD';
            var yBar  = yCenter - grosor / 2;

            // Nombre a la izquierda
            barrasHtml += '<text x="' + (padLeft - 8) + '" y="' + (yCenter + 4) +
                '" font-size="11" fill="#2C3E50" text-anchor="end">' +
                (inv.nombre.length > 22 ? inv.nombre.slice(0,20) + '…' : inv.nombre) +
                '</text>';

            // Barra principal
            barrasHtml += '<rect x="' + xIni + '" y="' + yBar +
                '" width="' + barW + '" height="' + grosor +
                '" rx="4" fill="' + color + '" opacity="0.85"' +
                ' data-nombre="' + inv.nombre.replace(/"/g,'') + '"' +
                ' data-monto="' + fmt(inv.monto) + '"' +
                ' data-tasa="' + inv.tasa_ea + '"' +
                ' data-retorno="' + fmt(inv.retorno_neto) + '"' +
                ' data-dias="' + inv.dias_restantes + '"' +
                ' data-instrumento="' + (NOMBRES[inv.instrumento] || inv.instrumento) + '"' +
                ' data-vence="' + fmtFecha(inv.fecha_vencimiento) + '"' +
                ' class="tl-bar" style="cursor:pointer;"/>';

            // Etiqueta de monto dentro/fuera de la barra
            if (barW > 60) {
                barrasHtml += '<text x="' + (xIni + barW / 2) + '" y="' + (yCenter + 4) +
                    '" font-size="10" fill="white" text-anchor="middle" pointer-events="none">' +
                    fmt(inv.monto) + '</text>';
            }

            // Etiqueta de fecha vencimiento
            barrasHtml += '<text x="' + (xFin + 4) + '" y="' + (yCenter + 4) +
                '" font-size="9" fill="#666">' + fmtFecha(inv.fecha_vencimiento) + '</text>';
        });

        // Leyenda de instrumentos
        var leyendaHtml = '';
        var lx = padLeft;
        Object.keys(COLORES).forEach(function(k) {
            leyendaHtml += '<rect x="' + lx + '" y="' + (svgH - 14) +
                '" width="12" height="12" rx="2" fill="' + COLORES[k] + '"/>';
            leyendaHtml += '<text x="' + (lx + 16) + '" y="' + (svgH - 4) +
                '" font-size="10" fill="#666">' + NOMBRES[k] + '</text>';
            lx += 130;
        });

        var svgHtml = '<svg width="100%" height="' + (svgH + 20) + '" viewBox="0 0 ' + svgW + ' ' + (svgH + 20) + '">' +
            ticksHtml + barrasHtml + leyendaHtml + '</svg>';

        // Tooltip div
        var tooltipHtml = '<div class="tl-tooltip" style="display:none;position:absolute;' +
            'background:#2C3E50;color:white;padding:8px 12px;border-radius:6px;' +
            'font-size:11px;line-height:1.6;pointer-events:none;z-index:9999;max-width:220px;"></div>';

        container.style.position = 'relative';
        container.innerHTML = svgHtml + tooltipHtml;

        // ── Tooltip interactivo ──────────────────────────────────────
        var tooltip = container.querySelector('.tl-tooltip');
        container.querySelectorAll('.tl-bar').forEach(function(bar) {
            bar.addEventListener('mouseenter', function(e) {
                tooltip.innerHTML =
                    '<strong>' + bar.dataset.nombre + '</strong><br>' +
                    bar.dataset.instrumento + '<br>' +
                    'Monto: ' + bar.dataset.monto + '<br>' +
                    'Tasa EA: ' + bar.dataset.tasa + '%<br>' +
                    'Retorno Neto: ' + bar.dataset.retorno + '<br>' +
                    'Vence: ' + bar.dataset.vence + '<br>' +
                    'Días restantes: ' + bar.dataset.dias;
                tooltip.style.display = 'block';
            });
            bar.addEventListener('mousemove', function(e) {
                var rect = container.getBoundingClientRect();
                tooltip.style.left = (e.clientX - rect.left + 12) + 'px';
                tooltip.style.top  = (e.clientY - rect.top  - 10) + 'px';
            });
            bar.addEventListener('mouseleave', function() {
                tooltip.style.display = 'none';
            });
        });
    }

    function cargarYRenderizar(container) {
        fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "sicone.inversion.temporal",
                    method: "get_timeline_data",
                    args: [],
                    kwargs: {}
                }
            })
        })
        .then(function(r){ return r.json(); })
        .then(function(resp){
            if (resp.result && resp.result.length > 0) {
                renderTimeline(container, resp.result);
            } else {
                container.innerHTML = '<p style="color:#999;padding:16px;text-align:center;">' +
                    'No hay inversiones activas para mostrar.</p>';
            }
        })
        .catch(function(e){
            console.warn('SICONE timeline RPC error:', e);
        });
    }

    function scanAndInit() {
        document.querySelectorAll('.sicone-timeline:not([data-tl-init])').forEach(function(el) {
            el.setAttribute('data-tl-init', '1');
            cargarYRenderizar(el);
        });
    }

    function arrancar() {
        if (!document.body) return;
        new MutationObserver(function(){ scanAndInit(); })
            .observe(document.body, {childList: true, subtree: true});
        setTimeout(scanAndInit, 300);
        setTimeout(scanAndInit, 1000);
        setTimeout(scanAndInit, 2000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", arrancar);
    } else {
        arrancar();
    }
})();
