/** @odoo-module alias=sicone.waterfall **/
(function () {
    "use strict";

    function fmt(v) {
        var a = Math.abs(v);
        var s = a >= 1e9 ? (a / 1e9).toFixed(1) + "B"
              : a >= 1e6 ? Math.round(a / 1e6) + "M"
              : Math.round(a / 1e3) + "K";
        return (v < 0 ? "-" : "") + "$" + s;
    }

    function renderChart(container, datos, SI) {
        if (!container.querySelector("canvas.wf-canvas")) {
            container.innerHTML = ""
                + "<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;'>"
                + "<span style='font-weight:600;font-size:13px;color:#2C3E50;'>Cash Flow Consolidado 2025</span>"
                + "<div style='display:flex;gap:6px;'>"
                + "<button class='wf-btn-mensual' style='font-size:11px;padding:3px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;background:#eee;'>Mensual</button>"
                + "<button class='wf-btn-anual' style='font-size:11px;padding:3px 10px;border:1px solid #ddd;border-radius:4px;cursor:pointer;background:transparent;'>Anual</button>"
                + "</div></div>"
                + "<div style='height:280px;position:relative;'><canvas class='wf-canvas'></canvas></div>";
        }
        var canvas = container.querySelector("canvas.wf-canvas");
        var btnM = container.querySelector(".wf-btn-mensual");
        var btnA = container.querySelector(".wf-btn-anual");
        if (!canvas) return;
        var chart = null, vista = "mensual";

        function bldM() {
            var lb = ["Inicio"], iv = [0], ig = [0], eg = [0], sl = [SI], b = SI;
            datos.forEach(function(d){ lb.push(d.mes);iv.push(b);ig.push(d.ing);eg.push(d.egr);sl.push(0);b=d.sal; });
            return {labels:lb,datasets:[
                {label:"Base",data:iv,backgroundColor:"transparent",stack:"s"},
                {label:"Ingreso",data:ig,backgroundColor:"#1D9E75",stack:"s"},
                {label:"Egreso",data:eg,backgroundColor:"#D85A30",stack:"s"},
                {label:"Saldo",data:sl,backgroundColor:"#378ADD",stack:"s"}]};
        }
        function bldA() {
            var ti=datos.reduce(function(a,d){return a+d.ing;},0);
            var te=datos.reduce(function(a,d){return a+d.egr;},0);
            var sf=datos[datos.length-1].sal;
            return {labels:["Saldo inicial","Ingresos 2025","Egresos 2025","Saldo final"],
                datasets:[
                    {label:"Base",data:[0,SI,SI+ti,0],backgroundColor:"transparent",stack:"s"},
                    {label:"Valor",data:[SI,ti,te,sf],backgroundColor:["#378ADD","#1D9E75","#D85A30","#378ADD"],stack:"s"}]};
        }
        function actBtns(){
            if(btnM)btnM.style.background=vista==="mensual"?"#eee":"transparent";
            if(btnA)btnA.style.background=vista==="anual"?"#eee":"transparent";
        }
        function render(){
            var data=vista==="mensual"?bldM():bldA();
            if(chart)chart.destroy();
            chart=new window.Chart(canvas.getContext("2d"),{type:"bar",data:data,
                options:{responsive:true,maintainAspectRatio:false,
                    plugins:{legend:{display:false},
                        tooltip:{callbacks:{label:function(c){return c.dataset.label==="Base"?null:c.dataset.label+": "+fmt(c.raw);}},
                            filter:function(i){return i.dataset.label!=="Base";}}},
                    scales:{x:{stacked:true,grid:{display:false},ticks:{font:{size:11}}},
                        y:{stacked:true,ticks:{callback:fmt,font:{size:10}},grid:{color:"rgba(0,0,0,0.05)"}}}}});
        }
        function setV(v){vista=v;actBtns();render();}
        if(btnM)btnM.addEventListener("click",function(){setV("mensual");});
        if(btnA)btnA.addEventListener("click",function(){setV("anual");});
        actBtns();
        render();
    }

    function cargarYRenderizar(container) {
        // Obtener datos via RPC
        fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "sicone.config.empresa",
                    method: "get_waterfall_data",
                    args: [],
                    kwargs: {}
                }
            })
        })
        .then(function(r){ return r.json(); })
        .then(function(resp){
            if (resp.result && resp.result.datos && resp.result.datos.length) {
                renderChart(container, resp.result.datos, resp.result.saldo_inicial);
            }
        })
        .catch(function(e){ console.warn("SICONE waterfall RPC error:", e); });
    }

    function scanAndInit(){
        document.querySelectorAll(".sicone-waterfall:not([data-wf-init])").forEach(function(el){
            el.setAttribute("data-wf-init","1");
            cargarYRenderizar(el);
        });
    }

    function arrancar(){
        if(!document.body) return;
        new MutationObserver(function(){scanAndInit();}).observe(document.body,{childList:true,subtree:true});
        setTimeout(scanAndInit,300);
        setTimeout(scanAndInit,1000);
        setTimeout(scanAndInit,2000);
    }
    if(document.readyState==="loading"){
        document.addEventListener("DOMContentLoaded", arrancar);
    } else {
        arrancar();
    }
})();
