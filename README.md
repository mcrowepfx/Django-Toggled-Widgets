# Django Toggled Widgets

This package makes it possible to toggle between fields in the Django admin. When a form containing toggled fields is submitted, any field that did not have visibility upon submission is automatically set empty in the cleaned data.

## Usage

1. Add "toggled_widgets" to your `INSTALLED_APPS setting.

2. Add `toggled_widgets.ToggledWidgetFormMixin` to the MRO of any form class that requires the toggle behavior.

3. Set the form class' `toggle_groups` attribute to an iterable of tuples that describe the toggle relationship.

4. Add `toggled_widgets.ToggledWidgetAdminMixin to the MRO of any model admin class that uses a form containing the toggle behavior.

5. Optionally add `toggled_widgets.ToggledWidgetMixin` to the MRO of the toggled widget classes in order to gain more control over the appearance of the toggle control (e.g. by defining the `metafield_label` to customize the toggle control's label).

## `ModelForm` configuration

In the simplest implementation, each element in the tuples contained in the form class' `toggle_groups` attribute is a string whose value is a field name. The admin form will provide a control to toggle between these fields. For example:

```python
class SomeModelForm(ToggledWidgetFormMixin, ModelForm):
    toggle_groups = [
        ('some_field', 'some_other_field')
    ]
```

Any element in the tuple may also be an iterable containing multiple field names. In this case, any field name past the first in this iterable will toggle sympathetically along with the field named in the first item.

```python
class SomeModelForm(ToggledWidgetFormMixin, ModelForm):
    toggle_groups = [
        ('some_field', ('some_other_field', 'some_third_field'))
    ]
```