// INTAN_RFQ_PORTAL_CUSTOM_FIELDS_MARKER v1
//
// Requested directly by the user 2026-09-25: 9 free-text supplier-quote
// fields (product name, CAS number, MOQ, price, incoterm, payment term,
// stock ready/not, lead time, important note — see intan-chem-erp's
// dev/config.py SUPPLIER_QUOTATION_ITEM_QUOTE_FIELDS) on the built-in
// Supplier Portal's /rfq/<name> page.
//
// Shipped via `web_include_js` (see ../../hooks.py) so it loads on every
// website/portal page — deliberately guarded to only act on /rfq/<name>
// pages where `window.doc` exists. Injects new inputs into each already-
// rendered `.rfq-item` row via DOM manipulation and mutates the SAME
// `window.doc.items[idx]` objects erpnext's own rfq.js already maintains
// for qty/rate, rather than overriding erpnext's shipped rfq_items.html/
// rfq.js templates directly — avoids relying on unconfirmed multi-app
// Jinja-include override precedence for a template path shared with
// erpnext (see ../overrides/rfq_item_custom_fields_patch.py's header for
// the full reasoning). That patch is the other required half: without it,
// erpnext's create_rfq_items() silently drops any field here when "Make
// Quotation" is clicked, since it only copies an explicit allowlist.
//
// Runs after rfq.js's own $(document).ready() (both fire on the same
// event; jQuery calls ready handlers in registration order, and this file
// loads after rfq.js in the page's <head>/<body>), so window.doc and the
// .rfq-item rows already exist by the time this runs.

(function () {
    var CUSTOM_FIELDS = [
        ["custom_product_name", "Product Name"],
        ["custom_cas_number", "CAS Number"],
        ["custom_moq", "MOQ"],
        ["custom_quoted_price", "Quoted Price"],
        ["custom_stock_status", "Stock Ready / Not Ready"],
        ["custom_incoterm", "Incoterm"],
        ["custom_payment_term", "Payment Term"],
        ["custom_lead_time_note", "Lead Time"],
        ["custom_important_note", "Important Note"],
    ];

    function update_item_field(idx, fieldname, value) {
        (window.doc.items || []).forEach(function (row) {
            if (row.idx === idx) row[fieldname] = value;
        });
    }

    function build_row_fields(item) {
        var $wrap = $('<div class="row intan-custom-fields" style="margin-top:6px;margin-bottom:6px;"></div>');
        CUSTOM_FIELDS.forEach(function (pair) {
            var fieldname = pair[0];
            var label = pair[1];
            var $col = $('<div class="col-sm-4 col-6" style="margin-bottom:6px;"></div>');
            $col.append(
                '<label class="text-muted small" style="display:block;margin-bottom:2px;">' + label + '</label>'
            );
            var $input = $(
                '<input type="text" class="form-control form-control-sm intan-custom-field">'
            );
            $input.attr('data-fieldname', fieldname);
            $input.attr('data-idx', item.idx);
            if (item[fieldname]) $input.val(item[fieldname]);
            $input.on('change', function () {
                var idx = parseFloat($(this).attr('data-idx'));
                update_item_field(idx, fieldname, $(this).val());
            });
            $col.append($input);
            $wrap.append($col);
        });
        return $wrap;
    }

    function init() {
        if (!/^\/rfq\//.test(window.location.pathname)) return;
        if (!window.doc || !Array.isArray(window.doc.items)) return;
        if ($('.intan-custom-fields').length) return; // already injected

        $('.rfq-item').each(function (i) {
            var item = window.doc.items[i];
            if (!item) return;
            $(this).append(build_row_fields(item));
        });
    }

    $(document).ready(function () {
        // rfq.js sets window.doc via an inline <script> block rendered
        // before this file's own <script src> tag executes, but give the
        // DOM one tick to settle (.rfq-item rows are server-rendered, not
        // built by rfq.js, so this is a small safety margin, not a real
        // race).
        setTimeout(init, 200);
    });
})();
