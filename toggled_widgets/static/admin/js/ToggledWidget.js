class ToggledWidget {
    constructor(jQuery, element) {
        this.jQuery = jQuery;
        this.element = element;
        this.fieldName = this.element.getAttribute('name');
        this.element.toggler = this;
        let context = new DjangoAdminFieldContext(this.element);
        this.row = context.row;
        let toggleId = this.element.getAttribute('data-toggle-id');
        let $fieldset = this.jQuery(context.fieldset);
        /* We don't actually care about the cohort fields, just the rows in
        which they appear. */
        let cohortRows = [];
        $fieldset.find(
            '[data-master-toggle-id="]' + toggleId + '"]'
        ).each(function() {
            let context = new DjangoAdminFieldContext(this);
            cohortRows.push(context.row);
        });
        this.cohortRows = cohortRows;
        this.others = this.jQuery(context.fieldset).find(
            '[data-toggle-id]:not([data-toggle-id="' + toggleId + '"])'
        ).get();
        /* Find the metafield. This works a bit differently in the context of
        an inline form versus a regular form. */
        let fieldsetContainerId = context.fieldset.parentElement.id;
        let metafieldName = this.element.getAttribute('data-metafield-name');
        /* If the parent of the fieldset has an id attribute, and it ends with
        a hyphen followed by a number, we're in an inline context. We'll need
        to chop the contents of that id off the field's name attribute to get
        the clean name, which is what the metafield expects to get as a value.
        */
        if (fieldsetContainerId && /-\d+$/.test(fieldsetContainerId)) {
            this.fieldName = this.fieldName.substr(fieldsetContainerId.length + 1);
        }
        this.metafield = $fieldset.find(
            'input[data-base-name="' + metafieldName + '"]'
        ).get(0);
    }
    
    get isVisible() {
        this.row.getAttribute('class').indexOf('hidden') == -1;
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

(function() {
    function prepareToggle(field) {
        if (field.paired !== undefined) {
            return;
        }
        field.context = new DjangoAdminFieldContext(field);
        var toggleID = field.getAttribute('data-toggle-id');
        // Find the paired field (set it to the HTML element, not the jQuery instance)
        var fieldset = django.jQuery(field.context.fieldset);
        field.paired = fieldset.find(
            '[data-toggle-pairing="' + toggleID + '"]'
        ).get(0);
        // Also find any fields that need to toggle in sympathy with this one
        field.cohorts = fieldset.find(
            '[data-master-toggle-id="' + toggleID + '"]'
        ).get();
        for (var i = 0; i < field.cohorts.length; i++) {
            field.cohorts[i].context = new DjangoAdminFieldContext(
                field.cohorts[i]
            );
        }
        field.isVisible = function() {
            if (this._visible === undefined) {
                this._visible = this.context.row.getAttribute('class').indexOf('hidden') == -1;
            }
            return this._visible;
        }.bind(field);
        field.setVisible = function(visible) {
            if (visible === undefined) {
                /* Read the existing visibility attribute and hide/unhide the
                field and any cohorts as necessary. */
                visible = this.isVisible();
            }
            else {
                this._visible = visible;
            }
            var jqMethod = visible ? 'removeClass' : 'addClass';
            django.jQuery(this.context.row)[jqMethod]('hidden');
            for (var i = 0; i < this.cohorts.length; i++) {
                django.jQuery(this.cohorts[i].context.row)[jqMethod]('hidden');
            }
        }.bind(field);
        /* Find the metafield. This works a bit differently in the context of an
        inline form versus a regular form. */
        var fieldsetContainerID = fieldset.parent().attr('id');
        var metafieldName = field.getAttribute('data-metafield-name');
        field.cleanName = field.getAttribute('name');
        /* If the parent of the fieldset has an id attribute, and it ends with
        a hyphen followed by a number, we're in an inline context. We'll need
        to chop the contents of that id off the field's name attribute to get
        the clean name, which is what the metafield expects to get as a value.
        */
        if (fieldsetContainerID && /-\d+$/.test(fieldsetContainerID)) {
            field.cleanName = field.cleanName.substr(fieldsetContainerID.length + 1);
        }
        field.metafield = fieldset.find('input[data-base-name="' + metafieldName + '"]').get(0);
        // Define the toggle behavior
        field.toggle = function(recurse) {
            if (this.isVisible()) {
                this.setVisible(false);
            }
            else {
                this.setVisible(true);
                this.metafield.value = this.cleanName;
            }
            if (recurse) {
                this.paired.toggle();
            }
        }.bind(field);
        var button = document.createElement('button');
        button.field = field;
        django.jQuery(button).attr({
            'class': 'button',
            'type': 'button'
        }).text(
            field.getAttribute('data-toggle-button-text')
        ).on('click', function() {
            this.field.toggle(true);
        });
        field.context.row.appendChild(button);
        // If the pairing on the other end is complete, trigger an event
        if (field.paired.paired) {
            django.jQuery(document).trigger('pairingReady', [field]);
        }
    }
    
    django.jQuery(function() {
        /* Don't prepare the fields in the invisible extra form that's there
        only to be cloned. */
        django.jQuery('.toggledWidget:not([name*="__prefix__"])').each(function() {
            prepareToggle(this);
        });
        /* Instead, listen for dynamic additions and prepare those fields when
        they are added. */
        django.jQuery(document).on('formset:added', function(event, $row, formsetName) {
            $row.find('.toggledWidget').each(function() {
                prepareToggle(this);
            });
        });
    });
})();