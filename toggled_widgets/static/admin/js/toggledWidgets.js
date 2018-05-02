(function() {
    function getModelPicker(field) {
        // DEBUG
        /*
        if (field.type == 'hidden') {
            var result = django.jQuery(field).siblings('a.modelPicker');
            if (result.length) {
                return result[0];
            }
        }
        */
    }
    
    function prepareToggle(field) {
        if (field.paired !== undefined) {
            return;
        }
        field.context = new DjangoAdminFieldContext(field);
        // Create the toggle button, but hold off on adding it to the DOM
        var button = document.createElement('button');
        button.setAttribute('class', 'button');
        button.setAttribute('type', 'button');
        button.appendChild(document.createTextNode(
            field.getAttribute('data-toggle-button-text')
        ));
        button.field = field;
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
        field.setVisibility = function(visible) {
            if (visible === undefined) {
                /* Read the existing visibility attribute and hide/unhide the
                field and any cohorts as necessary. */
                visible = Boolean(this.getAttribute('data-visible'));
            }
            else {
                this.setAttribute('data-visible', visible ? '1' : '');
            }
            var jqMethod = visible ? 'removeClass' : 'addClass';
            django.jQuery(this.context.row)[jqMethod]('hidden');
            for (var i = 0; i < this.cohorts.length; i++) {
                django.jQuery(this.cohorts[i].context.row)[jqMethod]('hidden');
            }
        }.bind(field);
        field.setVisibility();
        /* Find the metafield. This works a bit differently in the context of an
        inline form versus a regular form. */
        var fieldsetContainerID = fieldset.parent().attr('id');
        var metafieldName = field.getAttribute('data-metafield-name');
        field.cleanName = field.getAttribute('name');
        if (fieldsetContainerID) {
            /* If this field is the dummy hidden field that's just there to be
            cloned, the suffix will be "-empty" instead of a numeric index, which
            interferes with the logic we're using to find the corresponding
            metafield, so replace it with "__prefix__". */
            if (fieldsetContainerID.substr(-6) == '-empty') {
                fieldsetContainerID = fieldsetContainerID.substr(
                    0, fieldsetContainerID.length - 6
                ) + '-__prefix__';
            }
            metafieldName = fieldsetContainerID + '-' + metafieldName;
            field.cleanName = field.cleanName.substr(fieldsetContainerID.length + 1);
        }
        field.metafield = fieldset.find('input[name="' + metafieldName + '"]').get(0);
        // Define the toggle behavior
        field.toggle = function(recurse) {
            if (Boolean(this.getAttribute('data-visible'))) {
                this.setVisibility(false);
            }
            else {
                this.setVisibility(true);
                this.metafield.value = this.cleanName;
            }
            if (recurse) {
                this.paired.toggle();
            }
        }.bind(field);
        /* In inline contexts, one of the fields we'll be handling is an invisible
        one that's in the document for the purposes of being cloned to create new
        fieldsets. If one of the two fields involved in the pairing is a model
        picker that doesn't specify the use of the parent object as the reference,
        it will be useless to expose it, because it won't work until the instance
        is saved. In this case, if there is a field in the pair that isn't a model
        picker, expose it and prevent the toggle button from being added.
        */
        // DEBUG
        if (false && field.id.indexOf('__prefix__') > -1) {
            if (field.paired) {
                var fieldModelPicker = getModelPicker(field),
                    pairedFieldModelPicker = getModelPicker(field.paired);
                if (((fieldModelPicker && !pairedFieldModelPicker) || (!fieldModelPicker && pairedFieldModelPicker)) &&
                    (fieldModelPicker && field.getAttribute('data-visible') == 'true' &&
                     fieldModelPicker.getAttribute('class').indexOf('useParent') < 0))
                {
                    /* Make sure the paired field has been set up, since we're about to
                    trigger the toggler recursively. */
                    prepareToggle(field.paired);
                    field.toggle(true);
                }
            }
        }
        else {
            /* The help text happens to have a class on it that forces the button
            to be aligned the way I want. If this field doesn't have help text,
            we'll want to insert an element to fill the same role. */
            var row = django.jQuery(field.context.row);
            if (!row.find('div.help').length) {
                var clearDiv = document.createElement('div');
                clearDiv.setAttribute('style', 'clear: left');
                row.append(clearDiv);
            }
            row.append(button);
            // Set up the click handler
            django.jQuery(button).on('click', function() {
                this.field.toggle(true);
            });
        }
    }
    
    django.jQuery(document).ready(function() {
        django.jQuery('input[data-toggle-id]').each(function() {
            prepareToggle(this);
        });
        // Also listen for dynamic additions
        django.jQuery(document).on('formset:added', function(event, row, formsetName) {
            django.jQuery(row).find('input[data-toggle-id]').each(function() {
                prepareToggle(this);
            });
        });
    });
})();