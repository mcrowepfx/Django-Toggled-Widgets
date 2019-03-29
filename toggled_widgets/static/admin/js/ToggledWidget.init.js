django.jQuery(document).ready(function() {
    django.jQuery('.toggledWidget:not([name*="__prefix__"])').each(function() {
        new ToggledWidget(django.jQuery, this);
    });
    django.jQuery(document).on('formset:added', function(e, $row) {
        $row.find('.toggledWidget').each(function() {
            new ToggledWidget(django.jQuery, this);
        });
    });
});