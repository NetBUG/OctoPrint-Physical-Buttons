# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.settings
import octoprint.util
from octoprint.events import eventManager, Events
from flask import jsonify, request
import logging
import logging.handlers
import RPi.GPIO as GPIO


class PhysicalButtonsPlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.EventHandlerPlugin,
							octoprint.plugin.BlueprintPlugin):


	def initialize(self):
		self._logger.setLevel(logging.DEBUG)
		
		self._logger.info("Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		if GPIO.VERSION < "0.6":
			raise Exception("RPi.GPIO must be greater than 0.6")
			
		GPIO.setmode(GPIO.BOARD)
		GPIO.setwarnings(False)
		
		self._logger.info("Physical Buttons Plugin [%s] initialized..."%self._identifier)

	def on_after_startup(self):
		self.PIN_PAUSE = self._settings.get(["pause"])
		self.PIN_STOP = self._settings.get(["stop"])
		self.PIN_PREHEAT = self._settings.get(["preheat"])
		self.PIN_RESUME = self._settings.get(["resume"])
		self.PIN_X_PLUS = self._settings.get(["xplus"])
		self.PIN_X_MINUS = self._settings.get(["xminus"])
		self.PIN_Y_PLUS = self._settings.get(["yplus"])
		self.PIN_Y_MINUS = self._settings.get(["yminus"])
		self.PIN_Z_PLUS = self._settings.get(["zplus"])
		self.PIN_Z_MINUS = self._settings.get(["zminus"])
		self.BOUNCE = self._settings.get_int(["bounce"])
		self.STOPCODE = self._settings.get(["stopcode"])
		self.phys_btns = [self.PIN_PAUSE, self.PIN_STOP, self.PIN_PREHEAT, self.PIN_RESUME, self.PIN_X_PLUS, self.PIN_X_MINUS, self.PIN_Y_PLUS, self.PIN_Y_MINUS, self.PIN_Z_PLUS, self.PIN_Z_MINUS]

		for i in self.phys_btns:
		    if i and i != -1:
			self._logger.info("%s button setup on GPIO [%s]..."%(str(i), i))
			GPIO.setup(i, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		self.setup_gpio()
		#if self.PIN_STOP != -1:
		#	self._logger.info("Stop button setup on GPIO [%s]..."%self.PIN_STOP)
		#	GPIO.setup(self.PIN_STOP, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	def get_settings_defaults(self):
		return dict(
			pause = -1,
			stop = -1,
			resume = -1,
			preheat = -1,
			xplus = -1,
			xminus = -1,
			yplus = -1,
			yminus = -1,
			zplus = -1,
			zminus = -1,
			bounce = 300,
			stopcode = "M112"
		)

	@octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
	def check_status(self):
		state = "-1"
		if self.PIN_PAUSE != -1:
			state = "0" if GPIO.input(self.PIN_PAUSE) else "1"
		state2 = "-1"
		if self.PIN_STOP != -1:
			state2 = "0" if GPIO.input(self.PIN_STOP) else "1"
		state3 = "-1"
		if self.PIN_RESUME != -1:
			state3 = "0" if GPIO.input(self.PIN_RESUME) else "1"
		state4 = "-1"
		if self.PIN_PREHEAT != -1:
			state4 = "0" if GPIO.input(self.PIN_PREHEAT) else "1"
		xp = "-1"
		if self.PIN_X_PLUS != -1:
			xp = "0" if GPIO.input(self.PIN_X_PLUS) else "1"
		xm = "-1"
		if self.PIN_X_MINUS != -1:
			xm = "0" if GPIO.input(self.PIN_X_MINUS) else "1"
		yp = "-1"
		if self.PIN_Y_PLUS != -1:
			yp = "0" if GPIO.input(self.PIN_Y_PLUS) else "1"
		ym = "-1"
		if self.PIN_Y_MINUS != -1:
			ym = "0" if GPIO.input(self.PIN_Y_MINUS) else "1"
		zp = "-1"
		if self.PIN_Z_PLUS != -1:
			zp = "0" if GPIO.input(self.PIN_Z_PLUS) else "1"
		zm = "-1"
		if self.PIN_Z_MINUS != -1:
			zm = "0" if GPIO.input(self.PIN_Z_MINUS) else "1"
		status = "unknown"
		if self._printer.is_printing():
			status = "printing"
		if self._printer.is_ready():
			status = "ready"
		if self._printer.is_paused():
			status = "paused"
		return jsonify(pause=state, stop=state2, status=status, resume=state3, preheat=state4, x_plus=xp, x_minus=xm, y_plus=yp, y_minus=ym, z_plus=zp, z_minus=zm )

	def on_event(self, event, payload):
		if event == Events.PRINT_STARTED:
			self._logger.info("Printing started. Buttons enabled.")
			self.setup_gpio()
		elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
			self._logger.info("Printing stopped. Buttons disabled.")
			try:
				for i in self.phys_btns:
					GPIO.remove_event_detect(i)
			except:
				pass

	def setup_gpio(self):
		try:
		    for i in self.phys_btns:
			GPIO.remove_event_detect(i)
		except:
			pass
		for i in self.phys_btns:
		    if i != -1:
			GPIO.add_event_detect(i, GPIO.FALLING, callback=self.check_gpio, bouncetime=self.BOUNCE)

	def check_gpio(self, channel):
		self._logger.debug("Detected button [%s]"%channel)
		if channel == self.PIN_PAUSE:
			self._logger.debug("Pause button pushed")
			# self._logger.debug("Pause button ([%s]) state [%s]"%(channel, state))
			if self._printer.is_printing():
				self._printer.toggle_pause_print()
			elif self._printer.is_paused():
				self._printer.resume_print()
				# TODO: send npause command (CLear HALT)

		elif channel == self.PIN_STOP:
			self._logger.debug("Stop button pushed")
			# self._logger.debug("Stop button ([%s]) state [%s]"%(channel, state2))
			if self._printer.is_printing():
				# self._printer.cancel_print()
				self._printer.commands(self.STOPCODE)
			elif self._printer.is_paused():
				self._printer.cancel_print()
			# elif self._printer.is_ready():
			# 	self._printer.start_print()

		elif channel == self.PIN_PREHEAT:
			self._logger.debug("Preheat button pushed")
			if self._printer.is_printing() or self._printer.is_paused():
				pass
			else:
				self._printer.commands('M104 S190 T0')

		elif channel == self.PIN_X_PLUS:
			self._logger.debug("X+ button pushed")
			if self._printer.is_printing() or self._printer.is_paused():
				pass
			else:
				self._printer.commands('G91')
				self._printer.commands('G1 X10 F3600')


		elif channel == self.PIN_X_MINUS:
			self._logger.debug("X- button pushed")
			if self._printer.is_printing() or self._printer.is_paused():
				pass
			else:
				self._printer.commands('G91')
				self._printer.commands('G1 X-10 F3600')


		elif channel == self.PIN_Y_PLUS:
			self._logger.debug("Y+ button pushed")
			if self._printer.is_printing() or self._printer.is_paused():
				pass
			else:
				self._printer.commands('G91')
				self._printer.commands('G1 Y10 F3600')


		elif channel == self.PIN_Y_MINUS:
			self._logger.debug("Y- button pushed")
			if self._printer.is_printing() or self._printer.is_paused():
				pass
			else:
				self._printer.commands('G91')
				self._printer.commands('G1 Y-10 F3600')


		elif channel == self.PIN_Z_PLUS:
			self._logger.debug("Z+ button pushed")
			if self._printer.is_printing() or self._printer.is_paused():
				pass
			else:
				self._printer.commands('G91')
				self._printer.commands('G1 Z10 F3600')


		elif channel == self.PIN_Z_MINUS:
			self._logger.debug("Z- button pushed")
			if self._printer.is_printing() or self._printer.is_paused():
				pass
			else:
				self._printer.commands('G91')
				self._printer.commands('G1 Z-10 F3600')

	def get_version(self):
		return self._plugin_version

	def get_update_information(self):
		return dict(
			octoprint_physicalbuttons=dict(
				displayName="Physical Buttons",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="netlands",
				repo="Octoprint-Physical-Buttons",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/netlands/OctoPrint-Physical-Buttons/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "Physical Buttons"
__plugin_version__ = "0.0.2"
__plugin_description__ = "Use physical buttons to start, stop and pause printing."

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PhysicalButtonsPlugin()

