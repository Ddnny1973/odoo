(function () {
    "use strict";

    function measureTextWidth(text, element) {
        if (!text) return 0;
        var ctx = document.createElement('canvas').getContext('2d');
        var style = window.getComputedStyle(element);
        var font = (style.fontStyle ? style.fontStyle + ' ' : '') + (style.fontWeight ? style.fontWeight + ' ' : '') + style.fontSize + ' ' + style.fontFamily;
        ctx.font = font;
        return Math.ceil(ctx.measureText(text).width);
    }

    function ensureGroupWidths() {
        document.querySelectorAll('.o_list_view .o_group_row, .o_tree_view .o_group_row').forEach(function (row) {
            var firstCell = row.querySelector('td:first-child, th:first-child, .o_group_cell');
            if (!firstCell) return;
            var header = firstCell.querySelector('.o_group_header') || firstCell;
            var text = header.innerText ? header.innerText.trim() : '';
            if (!text) return;
            var w = measureTextWidth(text, header) + 48; // padding
            firstCell.style.minWidth = w + 'px';
            firstCell.style.width = 'auto';
            firstCell.style.whiteSpace = 'normal';
        });
    }

    var observer = new MutationObserver(function () {
        ensureGroupWidths();
    });

    function init() {
        ensureGroupWidths();
        var container = document.querySelector('.o_list_view .o_contents, .o_tree_view .o_contents');
        if (container) observer.observe(container, { childList: true, subtree: true });
        // adjust after group toggle
        document.addEventListener('click', function (ev) {
            if (ev.target && ev.target.closest && ev.target.closest('.o_group_toggle')) {
                setTimeout(ensureGroupWidths, 50);
            }
        });
        // also adjust on resize
        window.addEventListener('resize', function () { setTimeout(ensureGroupWidths, 100); });
        // make function available for manual testing from console
        window.gcEnsureGroupWidths = ensureGroupWidths;
    }

    // Initialize when assets loaded
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(init, 0);
    } else {
        document.addEventListener('DOMContentLoaded', init);
    }
})();