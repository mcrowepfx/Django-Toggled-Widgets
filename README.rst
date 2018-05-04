======================
Django Toggled Widgets
======================

This package makes it possible to toggle between fields in the Django admin. When a form containing toggled fields is submitted, any field that did not have visibility upon submission is automatically set empty in the cleaned data.

Usage
_____

1. Add "toggled_widgets" to your ``INSTALLED_APPS`` setting.

2. Create custom widget classes that inherit from ``toggled_widgets.ToggledWidget``. Set the ``toggle_button_text`` attribute on these classes to control the text displayed on the buttons that will control the toggling.

3. Add ``toggled_widgets.ToggledWidgetFormMixin`` to the MRO of any ModelForm instances containing fields that use toggled widgets.

4. Define the ModelForm's ``toggle_pairs`` class attribute as an iterable of two-tuples that describe the toggle relationship.

ModelForm Configuration
_______________________

In the simplest implementation, both elements in the tuple are names of fields whose widgets inherit from ``toggled_widgets.ToggledWidget``. The admin form will provide a control to toggle between these two fields. For example:

    class SomeModelForm(ToggledWidgetFormMixin, ModelForm):
        toggle_pairs = [
            ('some_field', 'some_other_field')
        ]
    
Either or both elements in the tuple may also be an iterable containing multiple field names. In this case, only the first field in the iterable must use a widget that inherits from ``toggled_widgets.ToggledWidget``; the remainder may be any field. The first field will present the toggle control, and the remaining fields in the iterable will toggle on and off in sympathy with the first. For example:

    class SomeModelForm(ToggledWidgetFormMixin, ModelForm):
        toggle_pairs = [
            ('some_field', ('some_other_field', 'some_third_field'))
        ]
        
ModelAdmin Configuration
________________________

The only situation in which any special ModelAdmin configuration required is when the instance overrides ``get_fieldsets()`` and/or ``get_fields()``. ``ToggledWidgetFormMixin.clean()`` makes a decision about which value from a toggled field pair to respect by looking at the value of a hidden metafield whose value contains the name of the field that was visible upon submission. If the aforementioned methods are overridden, their return values need to include the name of this metafield. The metafield's name will always be based on the first field in a toggle pairing; obtain it by passing that field name to the ``ToggledWidgetFormMixin.build_metafield_name()`` static method.
        
Event Hooks
___________

Client-side scripts may subscribe to the ``pairingReady`` event on ``document`` to take action when the pairing between two inputs has been set up. In addition to the event itself, listeners will be passed the ``<input>`` element that registered the readiness of the pairing. Note that this event is only triggered once per pairing.