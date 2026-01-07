odoo.define('gc_apartamentos.arrendatarios_control', function (require) {
    'use strict';

    var core = require('web.core');
    var _t = core._t;

    function getHabitadoValue() {
        var $container = $("[data-field='habitado_por'], [data-name='habitado_por']");
        if (!$container.length) {
            return false;
        }
        // Try select
        var $select = $container.find('select');
        if ($select.length) {
            return $select.val();
        }
        // Try radio inputs
        var $radio = $container.find("input[type='radio']:checked");
        if ($radio.length) {
            return $radio.val();
        }
        // Try inputs (some widgets use input value)
        var $input = $container.find("input[type!='radio']");
        if ($input.length) {
            return $input.first().val();
        }
        return false;
    }

    function setArrendatarioVisibility(show) {
        var $mm = $("[data-field='arrendatario_ids'], [data-name='arrendatario_ids']");
        if (!$mm.length) {
            console.debug('gc_apartamentos: arrendatario container not found');
            return;
        }
        console.debug('gc_apartamentos: setArrendatarioVisibility(show=', show, ')');
        if (show) {
            // Show the field wrapper (label + field)
            $mm.closest('.o_field, .o_field_widget, .o_form_group').show();
            $mm.show();
            $mm.removeClass('o_hidden o_readonly');
            $mm.removeAttr('aria-hidden');
        } else {
            // Hide the full wrapper so label + field disappear
            $mm.closest('.o_field, .o_field_widget, .o_form_group').hide();
            $mm.hide();
            $mm.addClass('o_hidden');
            $mm.attr('aria-hidden', 'true');
            // Optionally clear visible tags to avoid stale UI (actual model is cleaned by onchange)
            $mm.find('.badge, .o_tag, .o_tag_item').remove();
        }
    }

    function toggleArrendatario() {
        var hab = getHabitadoValue();
        var show = (hab === 'arrendatario');
        console.debug('gc_apartamentos: toggleArrendatario - habitado_por=', hab, ' show=', show);
        setArrendatarioVisibility(show);
    }

    function setupObservers() {
        var target = document.body;
        if (!window.__gc_arr_obs) {
            window.__gc_arr_obs = new MutationObserver(function (mutations) {
                mutations.forEach(function (mutation) {
                    var added = Array.from(mutation.addedNodes || []);
                    var relevant = added.some(function (n) {
                        try {
                            return (n.querySelector && (n.querySelector('[data-field="habitado_por"]') || n.querySelector('[data-field="arrendatario_ids"]') || n.querySelector('[data-name="habitado_por"]') || n.querySelector('[data-name="arrendatario_ids"]')));
                        } catch (e) {
                            return false;
                        }
                    });
                    if (relevant) {
                        console.debug('gc_apartamentos: MutationObserver triggered relevant addition');
                        toggleArrendatario();
                    }
                });
            });
            window.__gc_arr_obs.observe(target, { childList: true, subtree: true });
        }
    }

    $(document).ready(function () {
        // Expose a global helper to test
        window.gc_toggleArrendatario = toggleArrendatario;

        // Initial check
        toggleArrendatario();
        // Listen for changes in any select/radio/input inside habitado_por
        $(document).on('change', "[data-field='habitado_por'] input, [data-field='habitado_por'] select, [data-name='habitado_por'] input, [data-name='habitado_por'] select", function () {
            toggleArrendatario();
        });
        // Safety: also re-check when arrendatario container is inserted
        $(document).on('DOMNodeInserted', "[data-field='arrendatario_ids'], [data-name='arrendatario_ids']", function () {
            toggleArrendatario();
        });
        setupObservers();
    });
});