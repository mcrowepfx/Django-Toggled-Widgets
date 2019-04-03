class ToggledWidget {
    constructor(jQuery, element) {
        this.jQuery = jQuery;
        this.element = element;
        this.element.toggler = this;
        this.fieldName = this.element.getAttribute('name');
        let context = new DjangoAdminFieldContext(this.element);
        this.row = context.row;
        let toggleId = this.element.getAttribute('data-toggle-id');
        let $fieldset = this.jQuery(context.fieldset);
        /* We don't actually care about the cohort fields, just the rows in
        which they appear. */
        let cohortRows = [];
        $fieldset.find(
            '[data-master-toggle-id=' + toggleId + ']'
        ).each(function() {
            let context = new DjangoAdminFieldContext(this);
            cohortRows.push(context.row);
        });
        this.cohortRows = cohortRows;
        let selector = '[data-toggle-group-id=' + this.element.getAttribute('data-toggle-group-id') + ']' +
            // But not this one
            ':not([data-toggle-id="' + toggleId + '"])' +
            // And also not the metafield
            ':not(.toggle-metafield)';
        this.others = this.jQuery(context.fieldset).find(selector).get();
        let fieldsetContainerId = context.fieldset.parentElement.id;
        /* If the parent of the fieldset has an id attribute, and it ends with
        a hyphen followed by a number, we're in an inline context. We'll need
        to chop the contents of that id off the field's name attribute to get
        the clean name. */
        if (fieldsetContainerId && /-\d+$/.test(fieldsetContainerId)) {
            this.fieldName = this.fieldName.substr(fieldsetContainerId.length + 1);
        }
    }
    
    show() {
        this.jQuery(this.row).removeClass('hidden');
        for (let i = 0; i < this.cohortRows.length; i++) {
            this.jQuery(this.cohortRows[i]).removeClass('hidden');
        }
        for (let i = 0; i < this.others.length; i++) {
            this.others[i].toggler.hide();
        }
    }
    
    hide() {
        this.jQuery(this.row).addClass('hidden');
        for (let i = 0; i < this.cohortRows.length; i++) {
            this.jQuery(this.cohortRows[i]).addClass('hidden');
        }
    }
}

function initializeMetafield(field) {
    let toggledWidgets = {};
    django.jQuery(
        '[data-toggle-group-id=' + field.getAttribute('data-toggle-group-id') + '].toggled-widget'
    ).each(function() {
        toggledWidgets[this.toggler.fieldName] = this.toggler;
    });
    django.jQuery(field).on('change', function() {
        toggledWidgets[this.options[this.options.selectedIndex].value].show();
    });
    if (field.getAttribute('class').indexOf('toggle-button') > -1) {
        django.jQuery(field).on('mousedown', function(e) {
            if (e.which == 1) {
                e.preventDefault();
                /* The only two possible values for the selected index should be 0
                and 1. */
                this.options.selectedIndex = this.options.selectedIndex ? 0 : 1;
                django.jQuery(this).change();
            }
        });
    }
}