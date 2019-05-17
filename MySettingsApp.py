###############################################################################
# STACKOVERFLOW
#https://stackoverflow.com/questions/49514950/sanitize-validate-kivy-settings-user-input
###############################################################################


###############################################################################
# Version
###############################################################################

__version__ = '0.1'



###############################################################################
# Imports
###############################################################################


# Kivy
from kivy.app import App
from kivy.lang.builder import Builder

from kivy.uix.settings import Settings
from kivy.uix.settings import SettingString
from kivy.uix.settings import InterfaceWithNoMenu
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from kivy.logger import Logger




###############################################################################
# Constants
###############################################################################


JSON_MATH = '''
[
    {
        "type": "complex_operator_string",
        "title": "Operator (free choice)",
        "desc": "Choose the operator. + (addition). - (subtraction). * (multiplication). : (division). % (modulo). You can also choose any combination of those operations to create your own mix.",
        "section": "Math",
        "key": "operator"
    },
    {
        "type": "options",
        "title": "Operator (options)",
        "desc": "Choose the operator. + (addition). - (subtraction). * (multiplication). : (division). % (modulo). You can also choose from three mixes.",
        "options": ["+", "-", "*", ":", "%", "+-", "*:", "+-*:"],
        "section": "Math",
        "key": "operator_"
    }
]
'''

kv_string = """
<MySettingsRoot>:
    orientation: 'vertical'

    Label:
        text: '[b] My Settings App [/b]'
        markup: True

    Button:
        text: 'Settings'
        on_release: app.open_settings()

    Button:
        text: 'Quit'   
        on_release: app.stop()

<ValidatedSettings>:
    interface_cls: 'ValidatedSettingsInterface'
"""



###############################################################################
# Widgets
###############################################################################

class ValidatedSettingsInterface(InterfaceWithNoMenu):  
    pass

class ValidatedSettings(Settings):

    def __init__(self, **kwargs):
        super(ValidatedSettings, self).__init__(**kwargs)
        self.register_type('complex_operator_string', OperatorSetting)

    def add_kivy_panel(self):
        pass

class OperatorSetting(SettingString):

    def __init__(self, **kwargs):
        super(OperatorSetting, self).__init__(**kwargs)

    def _validate(self, instance):
        self._dismiss()    # closes the popup
        try:
            assert set(["+", "-", "*", ":", "%"]).union([str(v) for v in self.textinput.text]) == set(["+", "-", "*", ":", "%"])
            self.value = self.textinput.text
            Logger.info('App: Assertion is true, setting value to textinput')
        except AssertionError:
            Logger.info('App: This choice is forbidden.')
            return

        

###############################################################################
# Root Widget
###############################################################################

class MySettingsRoot(BoxLayout):
    """ See kv string
    """
    def __init__(self, *args, **kwargs):
        super(MySettingsRoot, self).__init__(*args, **kwargs)




###############################################################################
# App Object
###############################################################################

class MySettingsApp(App):
    """ App object
    """
    def __init__(self, *args, **kwargs):
        super(MySettingsApp, self).__init__(*args, **kwargs)
        self.settings_cls = ValidatedSettings         

    def build(self):
        Builder.load_string(kv_string)
        return MySettingsRoot()

    def build_config(self, config):
        config.setdefaults('Math', {'operator': '+-:%', 'operator_': '*'})
                
    def build_settings(self, settings):
        settings.add_json_panel('Math', self.config, data=JSON_MATH)
    

    
    def on_config_change(self, config, section, key, value, *args):
              
        if section == 'Math':

            if key == 'operator':

                Logger.info('App: Your operators via free choice: %s' %value)
                #self.root.calculation_screen.operation = ''.join([str(MathBackEnd.operator_strings.index(p)) for p in list(value)])                
                
            if key == 'operator_':
                
                Logger.info('App: Your operators via options: %s' %value)
                
        


if __name__ in ('__main__', '__android__'):
    MySettingsApp().run()
