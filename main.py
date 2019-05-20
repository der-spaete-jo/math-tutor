

###############################################################################
# Version
###############################################################################

__version__ = '0.1.14'

# TODO: fix game
# introduced checkpoint method in RespTimer class. But it does not work. its only called in on_current_answer method of CalcScreen.

# TODO until v1.0:
# split this file into many different files
# rename calculation.kv, CalculationApp, CalculationRoot, into CalculationGame...
# this is not backwardscompatible, therefore a major release 0.1 -> 1.0 (because the datatypes in CalcGameStats.txt have changed)
# create a button "reset Statistics". maybe as part of the statisticscreen. there should also be a popup asking "U sure mate?". -> the backend for this functionality is built, see StatisticScreen class.
# erase os from global imports. Only import it, when you need it (ensure_stats_file, reset_stats)
# what is the equivalent of webbrowser for android? Then the former todo applies: import it if you know that the platform is not android. Else import the equivalent.
# make webbrowser work in android. e.g.: https://github.com/kivy/kivy/wiki/Android-native-embedded-browser. android will be a requirement then. Don't forget to add the adroid recipe to buildozer.spec
# add numpy + recipe to requirements in buildozer.spec
# unify colors... or take away colors from statistic screen... or introduce color schemes and add them to the settings General. 
# Overall identity... ask jule for a font and some pics/icons!
# if a calculation game lasts longer than 1 minute(?) you may get negative response times (overflow error) -> some_timer_object[:-4] will likely be the reason... should be fixed now: ResponseTimer internally only handels datetime.datetime and datetime.timedelta objects. Only when they are displayed, they are sliced.
# get rid of the first case in generate_random_questions, then get rid of pick_random_number_pairs
# A higher difficulty just means a higher volatility in the difficulty of questions... you have to adjust the distribution of possible factors/summands/... or even take away some numbers as 2 or 5, in difficulty 4. see np.random.xyz e.g. np.random.choice
# fix popup for lr_btn bad value

# TODO until v1.1:
# google analytics http://cheparev.com/, http://cheparev.com/kivy-recipe-google-analytics-and-bug-monitoring/
# and advertisements https://github.com/kivy/kivy/wiki/AdBuddiz-Android-advertisements-integration-for-Kivy-apps, also https://github.com/MichaelStott/KivMob, 
# what can you do else? https://blog.kivy.org/2016/01/kivy-android-app%C2%A0showcase/, https://github.com/eviltnan/kognitivo





###############################################################################
# Imports
###############################################################################

# Local Modules
#from util.responsetimer import ResponseTimer
#from util.progresslabel import ProgressLabel
#from util.customscreens import CalculationScreen, StatisticScreen, PlotScreen, AboutScreen

# Standard Python
#import os                      # imported where needed
import operator                 # better handling of +, #, *, etc.
#import webbrowser              # access homepages via the about section, imported if platform not android
import random                   # create random math questions
import datetime                 # for the timer
import itertools                # eg for cycling colors
from functools import partial   # schedule callback functions that take arguments different from 'dt'

# Non-Standard Python
import numpy as np


# Kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, NumericProperty, StringProperty
from kivy.storage.dictstore import DictStore
from kivy.utils import get_color_from_hex as rgb

from kivy.uix.settings import Settings, SettingString
from kivy.uix.settings import InterfaceWithTabbedPanel
from kivy.uix.settings import SettingsWithTabbedPanel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup

from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.logger import Logger

# Kivy Garden
from kivy.garden.graph import Graph
from kivy.garden.graph import MeshLinePlot, SmoothLinePlot




###############################################################################
# Constants: Colors
###############################################################################

BACKGROUND_COLOR = [0,0,0,1]
TEXT_COLOR = [1,1,1,1]
TEXT_HIGHLIGHT_COLOR = rgb('ff0000')
AXIS_GREY = rgb('444444')
PLOT_BLUE = []
PLOT_GREEN = []
PLOT_RED = []
PLOT_YELLOW = []


###############################################################################
# Constants: Settings Data
###############################################################################



JSON_MATH = '''
[
	{
		"type": "options",
		"title": "Difficulty",
		"desc": "A higher difficulty increases the range of numbers that you need to compute.",
		"options": ["1", "2", "3", "4"],
		"section": "Math",
		"key": "diffclty"
	},
	{
		"type": "operator_free_choice",
		"title": "Operator",
		"desc": "Choose the operator. + (addition). - (subtraction). * (multiplication). : (division). % (modulo). Create your own mix, by combining those operators.",
		"section": "Math",
		"key": "operator"
	},
	{
		"type": "options",
		"title": "Number of Questions",
		"desc": "Choose how many questions comprise a calculation game: 8 or 16?.",
		"options": ["8", "16"],
		"section": "Math",
		"key": "num_of_qs"
	}
]
'''
JSON_GENERAL = '''
[
	{
		"type": "lr_btn_free_choice",
		"title": "Lower-Right Button",
		"desc": "Choose the functionality of the lower-right button on the keyboard. Choose from 'Submit', 'Back' or any digits, like '00'.",
		"section": "General",
		"key": "lr_btn"
	},  
	{
		"type": "bool",
		"title": "Show Timer",
		"desc": "Show the response timer in the top left corner during calculation games.",
		"section": "General",
		"key": "show_time"
	},
	{
		"type": "bool",
		"title": "Show Progress",
		"desc": "Show the progress in the top right corner calculation games.",
		"section": "General",
		"key": "show_progress"
	}
]
'''


###############################################################################
# BackEnd: Mathematics
###############################################################################


class MathBackEnd():
	
	operator_strings = ['+', '-', '*', ':', '%']
	operators = [operator.add, operator.sub, operator.mul, operator.truediv, operator.mod]
	difficulty_to_range = {'0': {'1': [(0,10), (0,10)],
								 '2': [(0,50), (0,10)],
								 '3': [(0,30), (0,30)],
								 '4': [(0,100), (0,100)]},
						   '1': {'1': [(0,10), (0,10)],
								 '2': [(0,50), (0,10)],
								 '3': [(0,30), (0,30)],
								 '4': [(0,100), (0,100)]},
						   '2': {'1': [(1,10), (1,10)],
								 '2': [(1,30), (1,10)],
								 '3': [(1,20), (1,20)],
								 '4': [(1,50), (1,50)]},
						   '3': {'1': [(1,10), (1,10)],
								 '2': [(1,30), (1,10)],
								 '3': [(1,20), (1,20)],
								 '4': [(1,50), (1,50)]},
						   '4': {'1': [(1,10), (1,10)],
								 '2': [(1,30), (1,10)],
								 '3': [(1,50), (1,20)],
								 '4': [(1,100), (1,50)]}}
	def __init__(self):
		pass
	
	@staticmethod
	def generate_random_questions(op = '0', diff = 1, N = 8):
		if len(op) == 1:
			# Only a single operation? Then just pick random number pairs.
			op = int(op)
			return MathBackEnd.pick_random_number_pairs(op, diff, N)
		else:
			# Mix of operators? Then ranges need to be adjusted per question.
			ops = np.array([int(p) for p in list(op)])

			P = np.random.choice(ops, size = (N,))
			# A = np.array([np.random.choice(range(MathBackEnd.difficulty_to_range[str(p)][str(diff)][0]), p=[0, 0, 1/n, 1/2n, 1/n, ...]) for p in P])   
			A = np.array([np.random.randint(low = MathBackEnd.difficulty_to_range[str(p)][str(diff)][0][0], high = MathBackEnd.difficulty_to_range[str(p)][str(diff)][0][1]) for p in P])
			B = np.array([np.random.randint(low = MathBackEnd.difficulty_to_range[str(p)][str(diff)][1][0], high = MathBackEnd.difficulty_to_range[str(p)][str(diff)][1][1]) for p in P])
			
			Q = np.array(list(zip(A, B, P)))
			for q in Q:

				if q[2] in (0, 2):
					pass
				elif q[2] in (1, 4): # sub or mod -> big - small ensures positive output
					if q[0] < q[1]:
						n = q[0]
						q[0] = q[1]
						q[1] = n
				elif q[2] == 3: # division -> ensure integer result...
					n = q[0]
					q[0] = q[0]*q[1]
					q[1] = n
			return Q

	@staticmethod
	def pick_random_number_pairs(op = 0, diff = 1, N = 8):
		range_a, range_b = MathBackEnd.difficulty_to_range[str(op)][str(diff)][0], MathBackEnd.difficulty_to_range[str(op)][str(diff)][1]
		
		A = np.random.randint(low = range_a[0], high = range_a[1], size = (N,))
		B = np.random.randint(low = range_b[0], high = range_b[1], size = (N,))
		P = np.array([op for i in range(N)])
		
		Q = np.array(list(zip(A, B, P)))
		
		if op in (0, 2):
			return Q
		if op in (1, 4): # sub or mod -> big - small ensures positive output
			return [(n[0], n[1], n[2]) if n[0]>=n[1] else (n[1], n[0], n[2]) for n in Q]
		if op == 3: # division -> ensure integer result...
			return [(n[0]*n[1], n[0], n[2]) for n in Q]

	@staticmethod
	def get_true_answer(q):
		""" 
			Input: tripel <q>
			Process: apply q[2] to q[0], q[1]
		"""
		return int(MathBackEnd.operators[q[2]](q[0], q[1]))

	@staticmethod
	def timedelta2seconds(response_time):
		"""
			Input: datetime.timedelta object 
		"""
		time_string = str(response_time)
		mins = int(time_string[2:4])
		secs = int(time_string[5:7])
		milli_secs = time_string[8:]
		time_in_sec = str(60*mins + secs) + '.' + milli_secs[:3]
		return time_in_sec

	@staticmethod
	def get_response_time_per_question(checkpoints):
		answer_time_per_question = checkpoints[:]
		i = len(answer_time_per_question) - 1
		time2 = checkpoints.pop()
		while checkpoints:
			time1 = checkpoints.pop()
			answer_time_per_question[i] = time2 - time1
			time2 = time1
			i = i - 1
		return answer_time_per_question

###############################################################################
# Widgets: Settings
###############################################################################

class ValidatedSettingsInterface(InterfaceWithTabbedPanel):  
	pass



class ValidatedSettings(Settings):

	def __init__(self, **kwargs):
		super(ValidatedSettings, self).__init__(**kwargs)
		self.register_type('operator_free_choice', OperatorSetting) 
		self.register_type('lr_btn_free_choice', LRButtonSetting)
		
	def add_kivy_panel(self):
		pass



class LRButtonSetting(SettingString):

	def __init__(self, **kwargs):
		super(LRButtonSetting, self).__init__(**kwargs)

	def _validate(self, instance):
		self._dismiss()    # closes the popup
		try:
			assert str(self.textinput.text) in ('Submit', 'Back', 'Joker') or self.textinput.text.isdigit()
			self.value = self.textinput.text
			Logger.info('LRButtonSetting: Assertion is true, setting value to textinput.')
		except AssertionError:
			Logger.info('LRButtonSetting: This choice is forbidden: %s.' %self.textinput.text)
			return




class OperatorSetting(SettingString):

	def __init__(self, **kwargs):
		super(OperatorSetting, self).__init__(**kwargs)

	def _validate(self, instance):
		self._dismiss()    # closes the popup
		try:
			assert set(["+", "-", "*", ":", "%"]).union([str(v) for v in self.textinput.text]) == set(["+", "-", "*", ":", "%"])        # this allows also "++*" in which case 2/3 of questions will be + and 1/3 *
			self.value = self.textinput.text
			Logger.info('OperatorSetting: Assertion is true, setting value to textinput.')
		except AssertionError:
			Logger.info('OperatorSetting: This choice is forbidden: %s.' %self.textinput.text)
			return





###############################################################################
# Widgets: Calculation Screen
###############################################################################

class ResponseTimer(Label):
	""" Timing each calculation game. """

	def __init__(self, *args, **kwargs):
		super(ResponseTimer, self).__init__(*args, **kwargs)
		
		self._start_time = 0
		self._cur_time = datetime.timedelta(0)
		self._pause_time = datetime.timedelta(0) 
		self._checkpoint = None
		self._checkpoints = []
		
		self.visibility = bool(int(App.get_running_app().config.get('General', 'show_time')))
		self.resp_timer = None

	def start_timing(self):
		self.text = ''
		
		self._start_time = datetime.datetime.now()
		self._cur_time = datetime.timedelta(0)
		self._pause_time = datetime.timedelta(0)
		self._checkpoint = None
		self._checkpoints = []
		
		self.resp_timer = Clock.schedule_interval(self._tick, 1/24)       
		
	def _tick(self, dt):
		now = datetime.datetime.now()
		self._cur_time = (now - self._start_time) - self._pause_time 
		self.text = str(self._cur_time)[2:-4] # '0:mn:xy.z' -> 'mn:xy.z'
		if self.visibility:
			self.color = TEXT_COLOR
		else:
			self.color = BACKGROUND_COLOR
			
	def snapshot(self):
		""" Returns the current total response time. 
		"""
		return self._cur_time

	def checkpoint(self):
		""" return the timedelta from now to the last checkpoint, 
			or the current total response time, if no checkpoint is defined.
		"""
		#if self._checkpoint:
		#	self._checkpoint = self._cur_time - self._checkpoint
		#else:
		#	self._checkpoint = self._cur_time
		self._checkpoints.append(self._cur_time)
		#return self._checkpoint

	def stop_timing(self):
		self.resp_timer.cancel()
		self.resp_timer = None
		
	def pause_timing(self):
		self._pause_start = datetime.datetime.now()
		self.resp_timer.cancel()
		self.resp_timer = 'paused'
		
	def resume_timing(self):
		self._pause_end = datetime.datetime.now()
		self._pause_time += self._pause_end - self._pause_start
		self.resp_timer = Clock.schedule_interval(self._tick, 1/24) 
		
		
		
class ProgressLabel(Label):
	""" Showing current question index as a fraction of the total numbers of questions. """
	def __init__(self, *args, **kwargs):
		super(ProgressLabel, self).__init__(*args, **kwargs)
		self.visibility = bool(int(App.get_running_app().config.get('General', 'show_progress')))
	
	def update(self, q_idx, num_q):
		""" Update the progress. """
		self.text = '%s/%s' %(q_idx + 1, num_q)
		if self.visibility:
			self.color = TEXT_COLOR
		else:
			self.color = BACKGROUND_COLOR



class NumPad(GridLayout):
	""" The key pad where users type in answers. """

	def __init__(self, *args, **kwargs):
		super(NumPad, self).__init__(*args, **kwargs)

		self.cols = 3
		self.spacing = 10
		self.lr_btn_text = str( App.get_running_app().config.get('General', 'lr_btn') )
		self.lower_right_button = Button(id='lower_right_button', text=self.lr_btn_text, on_release=self.on_numpad_button)
		self.create_buttons()

	def create_buttons(self):        
		nums = list(range(1, 10)) + ['Clear', 0]
		for n in nums:
			self.add_widget(Button(text=str(n), on_release=self.on_numpad_button))
		self.add_widget(self.lower_right_button)
	
	def on_numpad_button(self, btn):
		""" Callback function for all buttons that are part of the key pad """
		cs = App.get_running_app().root.ids.calculation_screen
		answer_text = cs.answer_text

		if btn.text.isdigit():
			# User presses a digit -> he wants to type in the solution
			answer_text.text += btn.text
			Clock.schedule_once(partial(cs.on_current_answer, answer_text, answer_text.text), 0)
		elif btn.text.lower() == 'clear':
			# Erase the answer text field
			answer_text.text = ''
		elif btn.text.lower() == 'submit' and answer_text.text != '':
			# User presses GO! and there exists an answer -> he wants to check it
			Clock.schedule_once(partial(cs.on_current_answer, answer_text, answer_text.text, 'submit'), 0)
		elif btn.text.lower() == 'back' and answer_text.text != '':
			answer_text.text = answer_text.text[:-1]
		elif btn.text.lower() == 'joker':
			answer_text.text = str(cs.get_answer())
			Clock.schedule_once(partial(cs.on_current_answer, answer_text, answer_text.text, 'joker'), int(cs.difficulty))



class CalculationScreen(Screen):
	""" Main class that rules the process of a calculation game.
	"""
	current_answer = StringProperty(0)
	#num_pad = ObjectProperty(None)
	def __init__(self, *args, **kwargs):
		super(CalculationScreen, self).__init__(*args, **kwargs)
		self.maths = MathBackEnd()
		
		# Attributes mirrored from MathBackEnd
		self.operators = MathBackEnd.operators
		self.operator_strings = MathBackEnd.operator_strings
		
		# Attributes set by user in the settings
		app_config = App.get_running_app().config
		self.operation = ''.join([str(MathBackEnd.operator_strings.index(p)) for p in list(app_config.get('Math', 'operator'))])      # \in {"0","1","2","3","4","01","23","0123"}
		self.difficulty = int(app_config.get('Math', 'diffclty'))
		self.num_questions = int(app_config.get('Math', 'num_of_qs'))

		# Attributes that correspond to one calculation game.
		# They are wiped on game initialization.
		self.current_question_index = 0
		self.questions = []
		self.answer_times = []
   
	def initialize_game(self):
		""" This method rules the initialization of a new calculation game.
			First it resets all relevant attributes of the calculation screen.
			Then it creates a list of questions to be asked during the game.
			Lastly it pops the first question and starts the game.
		"""
		# reset attributes, ...
		self.current_question_index = 0
		self.questions = []
		self.answer_times = []
		self.answer_text.text = ''
		# generate the whole series of questions, ...
		self.questions = MathBackEnd.generate_random_questions(self.operation, self.difficulty, self.num_questions,)
		# draw the first question...
		self.question_text.text = self.get_question()        
		# and start the timer!
		self.response_timer.start_timing()
		Logger.info('CalculationScreen: Initialized a new Calculation Game!')

	def get_question(self, question_index=-1):
		""" Returns the string representation (human readable) of the question with the given index.
			If no index is provided, the class attribute self.current_question_index is taken.
			If index is zero (start of a new game), then also the ResponseTimer is started.
			Last point is maybe bad, for reasons of logical code organization
		"""
		self.progress_label.update(self.current_question_index, self.num_questions)
		if question_index == -1:
			question_index = self.current_question_index
		
		q = self.questions[question_index]
		#return ' '.join( [str(q[0]), self.operator_strings[self.operation], str(q[1])] )
		return ' '.join( [str(q[0]), self.operator_strings[q[2]], str(q[1])] )

	def get_answer(self, question_index=-1):
		if question_index == -1:
			question_index = self.current_question_index 
		q = self.questions[question_index] 
		return MathBackEnd.get_true_answer(q)
	
	def switch_answer_text_color(self, *args):
		""" If the user submits a wrong answer, the answer_text is highlighted in red.
		"""
		if self.answer_text.color == TEXT_COLOR:
			self.answer_text.color = TEXT_HIGHLIGHT_COLOR
		else:
			self.answer_text.color = TEXT_COLOR
	
	def on_current_answer(self, instance, text, numpad_btn_name, *args):
		""" Listener to the StringProperty 'current_answer'.
			Automatically checks the solution given by user 
			If NumPad holds the 'Submit'-Button, the user can force the program to run this check. 

			The *args catches the dt-argument when on_current_answer is scheduled using Clock.schedule...
		"""
		idx = self.current_question_index
		true_answer = self.get_answer(idx)
		if int(text) == true_answer:
			# calculate time needed for this answer
			#shot = self.response_timer.snapshot()  # type datetime.timedelta
			#prev = sum(self.answer_times) if self.answer_times else datetime.timedelta(0)
			#respt = shot - prev
			#respt = self.response_timer.checkpoint()
			#self.answer_times.append(respt)
			#print(self.answer_times)
			# Log the correct answer
			#Logger.info('main.py: YAY! You calculated the correct solution. '
			#			'{0} = {1} in {2} sec'.format(self.question_text.text, true_answer, respt))
			# Set a checkpoint to calculate response times per question in the end.
			self.response_timer.checkpoint()
			
			if self.current_question_index < self.num_questions - 1:
				# pop the next question
				self.answer_text.text = ''
				self.current_question_index += 1
				self.question_text.text = self.get_question(self.current_question_index)
			else:
				Logger.info('main.py: Terminating current calculation game.') 
				# terminate current calculation game
				# snapshot and stop timer 
				total_resp_time = self.response_timer.snapshot()
				self.response_timer.stop_timing()
				self.answer_times = MathBackEnd.get_response_time_per_question(self.response_timer._checkpoints)
				# do calculations
				avg_resp_time = total_resp_time/self.num_questions
				min_resp_time = min(self.answer_times)
				max_resp_time = max(self.answer_times)
				# show them in the result screen              
				root = App.get_running_app().root
				root.result_screen.set_slicer(5)    # If total resp time is less than 1 min, this is ok
				root.result_screen.set_results(self.operation, self.difficulty, self.num_questions, self.questions, self.answer_times, total_resp_time, avg_resp_time, min_resp_time, max_resp_time)
				root.change_screen('result')
				print(self.response_timer._checkpoints)
		else:
			# Hightlight answer_text in red.
			if len(self.answer_text.text) >= len(str(true_answer)) or numpad_btn_name == 'submit':
				Clock.schedule_once(self.switch_answer_text_color, -1)
				Clock.schedule_once(self.switch_answer_text_color, 0.3)


###############################################################################
# Widgets: Result & Statistic Screen
###############################################################################


class ResultScreen(Screen):
	""" Is shown after each calculation game. Shows statistics about the game, like 
		average response time and minimum response time.
	"""
	def __init__(self, *args, **kwargs):
		super(ResultScreen, self).__init__(*args, **kwargs) 
		self.maths = MathBackEnd()
		self._slicer = slice(5, -4)    
	
	def set_slicer(self, a, b=-4):
		self._slicer = slice(a, b)


	def set_results(self, operation, difficulty, num_questions, questions, answer_times, tot_resp_time, avg_resp_time, min_resp_time, max_resp_time):
		""" Fill label texts with numerics.
			Save response times in the stats file.
		"""
		#self.total_response_time.text = str(tot_resp_time)[self._slicer] + 'sec'
		self.total_response_time.text = MathBackEnd.timedelta2seconds(tot_resp_time) + ' sec'
		self.average_response_time.text = MathBackEnd.timedelta2seconds(avg_resp_time) + ' sec'
		arg_min = answer_times.index(min(answer_times))
		arg_max = answer_times.index(max(answer_times))
		q_min = questions[arg_min]
		q_max = questions[arg_max]
		
		self.minimum_response_time.text = MathBackEnd.timedelta2seconds(min_resp_time) + ' sec' + '\n( ' + str(q_min[0]) + ' ' + MathBackEnd.operator_strings[q_min[2]] + ' ' + str(q_min[1]) + ' )'
		self.maximum_response_time.text = MathBackEnd.timedelta2seconds(max_resp_time) + ' sec' + '\n( ' + str(q_max[0]) + ' ' + MathBackEnd.operator_strings[q_max[2]] + ' ' + str(q_max[1]) + ' )'
		
		with open(App.get_running_app().stats_file, 'a') as f:
			f.write('{0},{1},{2},{3},{4},{5},{6},{7}\n'.format(datetime.datetime.now(), operation, difficulty, num_questions, tot_resp_time, avg_resp_time, min_resp_time, max_resp_time))
		
		

class StatisticScreen(Screen):
	""" Selection screen, where you can fix the parameters for 
		a pot of your statistics. 
	"""
	def __init__(self, *args, **kwargs):
		super(StatisticScreen, self).__init__(*args, **kwargs)       
		self.popup = None
		
	def _dismiss(self, *args):
		if self.textinput:
			self.textinput.focus = False
		if self.popup:
			self.popup.dismiss()
		self.popup = None

		
	def _reset_statistics(self, *args):
		self._dismiss()
		self.App.get_running_app().ensure_stats_file(override=True)
		
	def _create_popup(self):
		# create popup layout
		content = BoxLayout(orientation='vertical', spacing='5dp')
		popup_width = min(0.95 * Window.width, dp(500))
		self.popup = popup = Popup(
			title='Reset Statistics', content=content, size_hint=(None, None),
			size=(popup_width, '250dp'))

		sercurity_check_label = Label(text='U sure mate?')

		# construct the content, widget are used as a spacer
		content.add_widget(Widget())
		content.add_widget(sercurity_check_label)
		content.add_widget(Widget())
		content.add_widget(SettingSpacer())

		# 2 buttons are created for accept or cancel the current value
		btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
		btn = Button(text='Reset')
		btn.bind(on_release=self._reset_statistics)
		btnlayout.add_widget(btn)
		btn = Button(text='Cancel')
		btn.bind(on_release=self._dismiss)
		btnlayout.add_widget(btn)
		content.add_widget(btnlayout)

		# all done, open the popup !
		popup.open()

		
		
	def show_plot(self):
		""" 'onPlotButtonPress'
			callback for the 'plot'-Button on the bottom of StatisticScreen 
		"""
		op = MathBackEnd.operator_strings.index(self.stats_operation_spinner.text)
		diff = int(self.stats_difficulty_spinner.text)
		num_quest = int(self.stats_num_questions_button.text)


		with open(App.get_running_app().stats_file, 'r') as f:
			
			i = 0
			content = f.read()
			content_list = content.split('\n')
			A = np.array([np.array(L.split(',')) for L in content_list[1:]])
		""" # Some series for testing purposes...
		dummy_series = np.random.randint(1, 10, (12,))
		stmp_series = np.array([A[i][0] for i in range(len(A)-1)])    
		tot_series = np.array([float(A[i][4]) for i in range(len(A)-1)])
		avg_series = np.array([float(A[i][5]) for i in range(len(A)-1)])
		min_series = np.array([float(A[i][6]) for i in range(len(A)-1)])
		max_series = np.array([float(A[i][7]) for i in range(len(A)-1)])
		"""
		user_series = np.array([float(A[i][5][5:-4]) for i in range(len(A)-1) if A[i][1] == str(op) and int(A[i][2]) == diff and int(A[i][3]) == num_quest])
		if user_series.any():
			App.get_running_app().root.ids.plot_screen.create_kivy_plot(user_series)
			App.get_running_app().root.change_screen('plot')
		else:
			Logger.info('StatisticScreen: Cannot plot an empty graph.')
			popup = Popup(title='No Data', content=Label(text='There are no statistics available \nfor your selection.', halign='center'), size_hint=(None, None), size=(300, 300))
			popup.open()

	def switch_num_questions(self, instance, text):
		if int(text) == 16:
			instance.text = '8'
		else:
			instance.text = '16'

	

class PlotScreen(Screen):
	def __init__(self, *args, **kwargs):        
		super(PlotScreen, self).__init__(*args, **kwargs)
		self.graph_figure = None
		self.colors = itertools.cycle([rgb('7dac9f'), rgb('dc7062'), rgb('66a8d4'), rgb('e5b060')])
		

	
	def create_kivy_plot(self, series=np.array(range(12)), label_y='Average Response Time'):
		if self.graph_figure:
			self.destroy()

		series_len = len(series)
		if series_len == 0:
			return False
		max_y = max(series)
		min_y = min(series)
		#arg_max_y = series.index(max_y) # use this to label max and min... 
		#arg_min_y = series.index(min_y) # with their resp time stamp
		ticks_y = round(max_y/10., 2)


		graph_theme = {
				'label_options': {
					'color': rgb('444444'),  # color of tick labels and titles
					'bold': True},
				'background_color': rgb('000000'),  # back ground color of canvas
				'tick_color': rgb('444444'),  # ticks and grid
				'border_color': rgb('444444')}  # border drawn around each graph

		self.graph_figure = Graph(xlabel='Last {} games'.format(series_len), ylabel=label_y, x_ticks_minor=5, x_ticks_major=5, y_ticks_major=ticks_y, y_grid_label=True, x_grid_label=True, padding=10, x_grid=False, y_grid=True, xmin=0, xmax=series_len, ymin=0, ymax=int(1.2*max_y + 1), _with_stencilbuffer=False, **graph_theme)
		plot = SmoothLinePlot(color=next(self.colors)) #mode='line_strip', 
		plot.points = [(x, series[x-1]) for x in range(1, len(series)+1)]
		self.graph_figure.add_plot(plot)
		
		self.add_widget(self.graph_figure)

	def destroy(self): 
		""" This must be called before a new graph is plotted.
		"""
		self.remove_widget(self.graph_figure)
		self.graph_figure = None
		Logger.info('PlotScreen: Destroyed the child widget (the plot/graph) of PlotScreen')



###############################################################################
# Root Widget
###############################################################################

class CalculationRoot(BoxLayout):
	""" Root of all widgets
	"""
	calculation_screen = ObjectProperty(None)
	def __init__(self, *args, **kwargs):
		super(CalculationRoot, self).__init__(*args, **kwargs)
		self.screen_list = [] # previously visited screens


	def change_screen(self, next_screen):

		if self.screen_list == [] or self.ids.cg_screen_manager.current != self.screen_list[-1]:
			self.screen_list.append(self.ids.cg_screen_manager.current)

		if next_screen == 'start':
			self.ids.cg_screen_manager.current = 'StartScreen'
		elif next_screen == 'calculate':
			# Prepare the screen (generate the first assignment)
			calculation_screen = App.get_running_app().root.ids.calculation_screen
			calculation_screen.initialize_game()
			self.ids.cg_screen_manager.current = 'CalculationScreen'
		elif next_screen == 'statistic':
			self.ids.cg_screen_manager.current = 'StatisticScreen'          
		elif next_screen == 'about':
			self.ids.cg_screen_manager.current = 'AboutScreen'
		elif next_screen == 'result':
			self.ids.cg_screen_manager.current = 'ResultScreen'
		elif next_screen == 'plot':
			self.ids.cg_screen_manager.current = 'PlotScreen'       
		elif next_screen == 'quit':
			App.get_running_app().stop()

	def on_back_button_press(self):
		if self.screen_list:
			self.ids.cg_screen_manager.current = self.screen_list.pop()
			return True
		return False



###############################################################################
# App Object
###############################################################################

class CalculationApp(App):
	""" App object
	"""
	def __init__(self, *args, **kwargs):
		super(CalculationApp, self).__init__(*args, **kwargs)
		self.settings_cls = ValidatedSettings        
		self.difficulty = {'0': {'1': [(0,10), (0,10)],
								 '2': [(0,50), (0,10)],
								 '3': [(0,30), (0,30)],
								 '4': [(0,100), (0,100)]},
						   '1': {'1': [(0,10), (0,10)],
								 '2': [(0,50), (0,10)],
								 '3': [(0,30), (0,30)],
								 '4': [(0,100), (0,100)]},
						   '2': {'1': [(1,10), (1,10)],
								 '2': [(1,30), (1,10)],
								 '3': [(1,20), (1,20)],
								 '4': [(1,50), (1,50)]},
						   '3': {'1': [(1,10), (1,10)],
								 '2': [(1,30), (1,10)],
								 '3': [(1,20), (1,20)],
								 '4': [(1,50), (1,50)]},
						   '4': {'1': [(1,10), (1,10)],
								 '2': [(1,30), (1,10)],
								 '3': [(1,50), (1,20)],
								 '4': [(1,100), (1,50)]}}

	def get_about_text(self):
		return('This is all about mental calculation! '
				'You choose an operatior like "*" (multiplication) '
				'and this app will ask you a series of questions. '
				'You answer these questions using a build-in keypad.\n'
				'\n'
				'You may customize the look and functionality in the general settings.'
				'Check the math settings to change the operator, difficulty and number of questions. '
				'After each [b]Calculation Game[/b] you will get an '
				'overview of your performance, including total and average response times.'
				'To investigate your development, have a look at the Statistics. \n'
				'\n'
				'The app was built with [u][ref=py]Python 2[/ref][/u] and '
				'the [u][ref=kivy]Kivy framework[/ref][/u].\n'
				'\n'
				'This app is licensed under GNU GPLv3. \n'
				'Copyright 2018 Johannes Katzer. \n'
				'\n'
				'[i]Have Fun Calculating![/i]')

	def on_ref_press(self, instance, ref):
		references = {'kivy': 'www.kivy.org/#home', 
						'py': 'www.python.org',
						'4r6o': 'www.twitter.com/4r6o',
						'homepage': 'www.4r6o.de'}
		webbrowser.open(references[ref])

	def key_handler(self, *args):
		key = args[1]
		print(key)

		if key in (1000, 27):
			return self.root.on_back_button_press()

	def post_build_init(self, ev):
		if platform == 'android':
			# import androids webbrowser.
			pass
		else:
			import webbrowser
		win = self._app_window
		win.bind(on_keyboard = self.key_handler)
	
	def ensure_stats_file(self, override=False):
		import os
		
		if override and os.path.exists(self.stats_file):
			os.remove(self.stats_file)
		elif override and not os.path.exists(self.stats_file):
			Logger.info('main.py: Cannot override statistics file as it does not exist.')
			
		self.root_folder = self.user_data_dir
		self.cache_folder = os.path.join(self.root_folder, 'cache')
		if not os.path.exists(self.cache_folder):
			os.makedirs(self.cache_folder)
			Logger.info('main.py: Created new chache folder %s' % self.cache_folder)

		self.stats_file = os.path.join(self.cache_folder, 'CalcGameStats.txt')        
		if not os.path.exists(self.stats_file):
			with open(self.stats_file, 'w') as f:
				f.write('time_stamp,operation,difficulty,num_questions,total,average,minimum,maximum\n')  
			Logger.info('main.py: Created new statistics file %s' % self.stats_file)
   
	def on_pause(self):
		timer = self.root.response_timer
		if timer.resp_timer:
			timer.pause_timing()
		return True
		
	def on_resume(self):
		timer = self.root.response_timer
		if timer.resp_timer:
			timer.pause_timing()
		
	def build(self):
		self.bind(on_start=self.post_build_init)
		self.ensure_stats_file()
		return CalculationRoot()

	def build_config(self, config):
		config.setdefaults('General', {'lr_btn': 'Submit', 'show_time': '1', 'show_progress': '1'})
		config.setdefaults('Math', {'operator': '*', 'diffclty': '1', 'num_of_qs': '8'})
		
		
	def build_settings(self, settings):
		settings.add_json_panel('General', self.config, data=JSON_GENERAL)
		settings.add_json_panel('Math', self.config, data=JSON_MATH)
	
	
	
	def on_config_change(self, config, section, key, value, *args):

		if section == 'General':

			if key == 'lr_btn':
				if str(value) in ('Submit', 'Back', 'Joker') or value.isdigit():
					self.root.calculation_screen.num_pad.lr_btn_text = str(value)
					App.get_running_app().root.ids.calculation_screen.num_pad.lower_right_button.text = str(value)
				else:
					# Throw a popup warning: although settings value will be changed, it will have no effect on gameplay.
					popup_box = BoxLayout()
					popup_label = Label(text='This is not a valid option. This setting will have no effect. This is some more text that needs to be displayed.', halign='center', text_size=popup_box.size)
					popup_box.add_widget(popup_label)
					popup = Popup(title='Not A Valid Option', content=popup_box, size_hint=(None, None), size=(300, 300))
					popup.open()
				
			if key == 'show_time':
				# bool -> no validation needed
				self.root.calculation_screen.response_timer.visibility = bool(int(value))   # '0' -> False, '1' -> True
			if key == 'show_progress':
				# bool -> no validation needed
				self.root.calculation_screen.progress_label.visibility = bool(int(value))
				
		if section == 'Math':
		
			if key == 'diffclty':
					
				self.root.calculation_screen.difficulty = int(value)
				
			if key == 'operator':
				
				self.root.calculation_screen.operation = ''.join([str(MathBackEnd.operator_strings.index(p)) for p in list(value)])                

			if key == 'num_of_qs':
			
				self.root .calculation_screen.num_questions = int(value)



if __name__ in ('__main__', '__android__'):
	CalculationApp().run()

















''' Input validation
in App.build(): 
		self.config.add_callback(self.config_input_validation)
		
		
def config_input_validation(self, section, key, value, *args):
		""" Callback function, which is bound to the same event as on_config_change.

			It is supposed to validate the value that a user sets some setting to.
			It is being called, but config.set and config.write just don't work.
			
			However, if the app is restartet, all settings that are not valid, are 
			changed to valid values. This is realy wired!
		"""
		
					
		if section == 'General':
			if key == 'lr_btn':
				
				if not(str(value) in ('Submit', 'Back', 'Joker') or value.isdigit()):
					self.root.calculation_screen.num_pad.lr_btn_text = 'Submit'
					self.config.set('General', 'lr_btn', 'Submit')
					self.config.write()
					

if section == 'Math':
			if key == 'diffclty':
		   
				if float(value) > 4:
					value = '4'
					Logger.info('Difficulty 4 is maximum')
					#Clock.schedule_once(partial(self.config.set, 'Math', 'diffclty', value))
					#self.config.write()

					#Clock.schedule_once(self.close_settings)
					#Clock.schedule_once(partial(self.on_config_change, self.config, 'Math', 'diffclty', value))
					#Clock.schedule_once(self.open_settings, 1)
					
				if float(value) < 1:
					value = '1'
					Logger.info('Difficulty 1 is minimum')
'''


"""
	def updatePandasData(self, *args):
		cols = 'time_stamp,operation,difficulty,num_questions,total,average,minimum,maximum'.split(',')
		vals = [operation, difficulty, num_questions, self.total_response_time.text, self.average_response_time.text, self.minimum_response_time.text.split('\n')[0], self.maximum_response_time.text.split('\n')[0]]

		new_entry_data = {n: [d,] for n, d in zip(cols, vals)}
		print(new_entry_data)
		new_entry = pd.DataFrame(data=new_entry_data, columns=cols)
		stats_df = pd.read_pickle(App.get_running_app().stats_file)
		pd.concat([stats_df, new_entry])	# concat?
		stats_df.to_pickle(App.get_running_app().stats_file)
"""

"""
if PANDAS_AVAILABLE and MATPLOTLIB_AVAILABLE:
			self.stats_file = os.path.join(self.cache_folder, 'stats.pkl')
			#print(self.root_folder)

			if not os.path.exists(self.stats_file):
				df = pd.DataFrame(data=[], columns='operation,difficulty,num_questions,total,average,minimum,maximum'.split(',')) # header? 
				df.to_pickle(self.stats_file)
				Logger.info('main.py: Created new statistics file %s' % self.stats_file)

"""

"""
	def createMatplotlibPlot(self, series = np.array(range(12))):
		if self.graph_figure:
			self.destroy()
		fig, ax = plt.subplots()
		ax.plot(series)
		self.graph_figure = FigureCanvasKivyAgg(figure=fig)
		
		self.add_widget(self.graph_figure)
"""

"""
		if PANDAS_AVAILABLE and MATPLOTLIB_AVAILABLE: 
			stats_df = pd.read_pickle(App.get_running_app().stats_file)
			#stats_a = stats[stats['operation'] == 0]
			stats_a8 = stats_a[stats_a['questions'] == 8]
			series = stats_df.average
			dummy_series = np.random.randint(1, 10, (12,))

			App.get_running_app().root.ids.plot_screen.createMatplotlibPlot(series)
			App.get_running_app().root.change_screen('plot')

"""

"""

try:
	raise ImportError
	import matplotlib.pyplot as plt
	from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
	MATPLOTLIB_AVAILABLE = True

except ImportError:
	plt = None
	MATPLOTLIB_AVAILABLE = False
	Logger.info("main.py: Missing matplotlib.")
try:
	raise ImportError
	import pandas as pd
	PANDAS_AVAILABLE = True
except ImportError:
	pd = None
	PANDAS_AVAILABLE = False
	Logger.info("main.py: Missing pandas.")

"""
