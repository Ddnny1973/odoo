/** @odoo-module alias=sicone.proyeccion **/
(function () {
    "use strict";

    function renderProyChart(container, datos) {
        if (!container.querySelector("canvas.proy-canvas")) {
            container.innerHTML =
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                + '<span style="font-weight:600;font-size:13px;color:#1B4332;">Saldo de Caja — Historico + Proyecciones</span>'
                + '<small style="color:#6c757d;">Cifras en millones COP · Punteado = proyectado</small>'
                + '</div>'
                + '<div style="height:320px;position:relative;"><canvas class="proy-canvas"></canvas></div>';
        }

        var canvas = container.querySelector("canvas.proy-canvas");
        if (!canvas) return;
        if (canvas._ci) { canvas._ci.destroy(); }

        var lh = datos.labels_hist || [];
        var lp = datos.labels_proy || [];
        // Todos los labels: historicos + proyectados (sin duplicar el punto de union)
        var labelsAll = lh.concat(lp.filter(function(l){ return lh.indexOf(l) === -1; }));
        var nH = lh.length;

        // Dataset historico: datos reales, luego null
        var histFull = (datos.hist || []).concat(new Array(lp.length - 1).fill(null));

        // Proyectados: null hasta el penultimo historico, luego los valores (punto de union incluido)
        function mkProy(vals) {
            return new Array(nH - 1).fill(null).concat(vals || []);
        }

        canvas._ci = new window.Chart(canvas.getContext("2d"), {
            type: "line",
            data: {
                labels: labelsAll,
                datasets: [
                    {
                        label: "Historico",
                        data: histFull,
                        borderColor: "#6C757D",
                        backgroundColor: "rgba(108,117,125,0.07)",
                        borderWidth: 2.5,
                        pointRadius: 3,
                        tension: 0.3,
                        fill: true,
                    },
                    {
                        label: "Conservador",
                        data: mkProy(datos.conservador),
                        borderColor: "#2980B9",
                        borderWidth: 2,
                        borderDash: [6, 4],
                        pointRadius: 4,
                        tension: 0.3,
                        fill: false,
                    },
                    {
                        label: "Moderado",
                        data: mkProy(datos.moderado),
                        borderColor: "#E67E22",
                        borderWidth: 2,
                        borderDash: [6, 4],
                        pointRadius: 4,
                        tension: 0.3,
                        fill: false,
                    },
                    {
                        label: "Optimista",
                        data: mkProy(datos.optimista),
                        borderColor: "#27AE60",
                        borderWidth: 2,
                        borderDash: [6, 4],
                        pointRadius: 4,
                        tension: 0.3,
                        fill: false,
                    },
                    {
                        label: "Burn Rate Promedio",
                        data: new Array(labelsAll.length).fill(datos.burn_promedio || 0),
                        borderColor: "#E74C3C",
                        borderWidth: 3,
                        borderDash: [8, 4],
                        pointRadius: 0,
                        tension: 0,
                        fill: false,
                    },
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { position: "top" },
                    tooltip: {
                        callbacks: {
                            label: function(c) {
                                var v = c.parsed.y;
                                return v === null ? null :
                                    c.dataset.label + ": $" + v.toFixed(1) + "M";
                            }
                        }
                    }
                },
                scales: {
                    x: { ticks: { maxRotation: 45, font: { size: 10 } } },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(v) { return "$" + v + "M"; },
                            font: { size: 10 }
                        }
                    }
                }
            }
        });
    }

    function cargarYRenderizar(container) {
        var recordId = parseInt(container.getAttribute("data-record-id") || "0", 10);
        if (!recordId) return;

        fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "sicone.proyeccion.gerencial",
                    method: "get_proyeccion_data",
                    args: [[recordId]],
                    kwargs: {}
                }
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(resp) {
            if (resp.result && resp.result.labels_hist) {
                renderProyChart(container, resp.result);
            } else {
                container.innerHTML = '<p style="color:#999;padding:16px;">Sin datos — calcule primero las proyecciones.</p>';
            }
        })
        .catch(function(e) {
            console.warn("SICONE proyeccion RPC error:", e);
        });
    }

    function scanAndInit() {
        document.querySelectorAll(".sicone-proyeccion-chart:not([data-proy-init])").forEach(function(el) {
            el.setAttribute("data-proy-init", "1");
            cargarYRenderizar(el);
        });
    }

    function arrancar() {
        if (!document.body) return;
        new MutationObserver(function() { scanAndInit(); }).observe(document.body, { childList: true, subtree: true });
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
