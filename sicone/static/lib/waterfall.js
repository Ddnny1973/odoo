/**
 * SICONE Waterfall Widget — vanilla JS, sin dependencias OWL
 */
(function () {
    "use strict";

    function fmt(v) {
        var a = Math.abs(v);
        var s = a >= 1e9 ? (a / 1e9).toFixed(1) + "B"
              : a >= 1e6 ? Math.round(a / 1e6) + "M"
              : Math.round(a / 1e3) + "K";
        return (v < 0 ? "-" : "") + "$" + s;
    }

    function initWaterfall(container) {
        var raw = container.getAttribute("data-consolidado");
        var siRaw = container.getAttribute("data-saldo-inicial");
        if (!raw || !siRaw) return;
        var datos, SI;
        try { datos = JSON.parse(raw); SI = parseFloat(siRaw); } catch (e) { return; }

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

        if(window.Chart){ render(); }
        else {
            var s=document.createElement("script");
            s.src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js";
            s.onload=render;
            document.head.appendChild(s);
        }
    }

    function scanAndInit(){
        document.querySelectorAll(".sicone-waterfall:not([data-wf-init])").forEach(function(el){
            el.setAttribute("data-wf-init","1");
            initWaterfall(el);
        });
    }

    new MutationObserver(function(){scanAndInit();}).observe(document.body,{childList:true,subtree:true});
    setTimeout(scanAndInit,300);
    setTimeout(scanAndInit,1000);
    setTimeout(scanAndInit,2000);
})();
