======================
Django Toggled Widgets
======================

This package makes it possible to toggle between fields in the Django admin. When a form containing toggled fields is submitted, any field that did not have visibility upon submission is automatically set empty in the cleaned data.

Usage
_____

1. Add "toggled_widgets" to your ``INSTALLED_APPS`` setting.

2. Create custom widget classes that inherit from ``toggled_widgets.ToggledWidget``.

3. Add ``toggled_widgets.ToggledWidgetFormMixin`` to the MRO of any ModelForm instances containing fields that use toggled widgets.

4. Define the ModelForm's ``toggle_pairs`` class attribute as an iterable of two-tuples that describe the toggle relationship.

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