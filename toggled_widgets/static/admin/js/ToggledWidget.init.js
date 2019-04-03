django.jQuery(document).ready(function() {
    django.jQuery('.toggled-widget:not([name*="__prefix__"])').each(function() {
        new ToggledWidget(django.jQuery, this);
    });
    django.jQuery('.toggle-metafield:not([name*="__prefix__"])').each(function() {
        initializeMetafield(this);
    });
    django.jQuery(document).on('formset:added', function(e, $row) {
        $row.find('.toggled-widget').each(function() {
            new ToggledWidget(django.jQuery, this);
        });
        $row.find('.toggle-metafield').each(function() {
            initializeMetafield(this);
        });
    });
});