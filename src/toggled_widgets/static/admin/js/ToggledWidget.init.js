(function($) {
    $(function() {
        $('.toggled-widget:not([name*="__prefix__"])').each(function() {
            new ToggledWidget($, this);
        });
        $('.toggle-metafield:not([name*="__prefix__"])').each(function() {
            initializeMetafield(this);
        });
        $(document).on('formset:added', function(e, $row) {
            $row.find('.toggled-widget').each(function() {
                new ToggledWidget($, this);
            });
            $row.find('.toggle-metafield').each(function() {
                initializeMetafield(this);
            });
        });
    });
})(django.jQuery);