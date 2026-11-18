# -*- coding: UTF-8 -*-
# NVDA app module for LocalSend (localsend_app.exe)
# Author: Mohammed Al-Fehaida

import appModuleHandler
import api
import ui
import winUser
import languageHandler
from controlTypes import Role
from scriptHandler import script
from logHandler import log

_errCount = [0]

_AR = (languageHandler.getLanguage() or "").startswith("ar")

def _t(en, ar):
	return ar if _AR else en

L_HISTORY = _t("Receive history", "سجل الاستلام")
L_INFO = _t("Network info", "معلومات الشبكة")
L_START = _t("Start", "تشغيل")
L_RESTART = _t("Restart", "إعادة التشغيل")
L_STOP = _t("Stop", "إيقاف")
L_NEXT = _t("Button next to %s", "زر بجانب %s")
CAT = _t("LocalSend", "LocalSend")


# Known setting labels per section (English UI, default view). Used when the section is partly scrolled
# off screen, because LocalSend then leaves the hidden labels out of the section name.
_SEED = {
	"General": ["Theme", "Color", "Language", "Minimize to the System Tray/Menu Bar when closing", "Autostart after login", "Animations"],
	"Receive": ["Quick Save", 'Quick Save for "Favorites"', "Require PIN", "Save to folder", "Auto Finish", "Save to history"],
	"Network": ["Server", "Device name"],
	"Other": ["About LocalSend", "Support LocalSend", "Privacy Policy"],
}
_CACHE = {}
# Control "shape" of each section: B = named button, b = unnamed button, c = check box.
# Used when LocalSend reports the wrong parent for controls scrolled off screen.
_SIGS = {"BBBccc": "General", "cccBcc": "Receive", "bbb": "Network", "BBB": "Other"}


def _children(obj):
	try:
		return obj.children or []
	except Exception:
		return []


def _walk(obj, depth=0, maxDepth=20):
	if depth > maxDepth:
		return
	for c in _children(obj):
		yield c
		yield from _walk(c, depth + 1, maxDepth)


def _left(o):
	try:
		return o.location.left
	except Exception:
		return 0


def _top(o):
	try:
		return o.location.top
	except Exception:
		return 0


def _clickAt(x, y):
	old = winUser.getCursorPos()
	winUser.setCursorPos(int(x), int(y))
	winUser.mouse_event(winUser.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
	winUser.mouse_event(winUser.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
	try:
		winUser.setCursorPos(*old)
	except Exception:
		pass


def _clickObj(obj):
	loc = obj.location
	if not loc or loc.width <= 0:
		return False
	_clickAt(loc.left + loc.width / 2, loc.top + loc.height / 2)
	return True


class AppModule(appModuleHandler.AppModule):

	_busy = False

	def event_NVDAObject_init(self, obj):
		# Guard: looking at parents/siblings creates new objects, which fire this event again.
		if AppModule._busy:
			return
		AppModule._busy = True
		try:
			self._fixObject(obj)
		except Exception:
			if _errCount[0] < 5:
				_errCount[0] += 1
				log.exception("LocalSendAccess: error naming object")
		finally:
			AppModule._busy = False

	def _fixObject(self, obj):
		role = obj.role
		if role == Role.STATICTEXT:
			name = obj.name or ""
			# Side navigation items come through as plain text: "Receive\nTab 1 of 3"
			if "\n" in name:
				first, rest = name.split("\n", 1)
				if any(ch.isdigit() for ch in rest):
					obj.role = Role.TAB
					obj.name = first
					obj.description = rest
			return
		if role == Role.GROUPING:
			gname = obj.name or ""
			if "\n" in gname:
				# Section header: keep only its title, the rest are labels of its controls
				obj.name = gname.split("\n", 1)[0]
			return
		if role not in (Role.BUTTON, Role.CHECKBOX):
			return
		name = (obj.name or "").strip()
		parent = obj.parent
		if parent is None:
			return
		pname = (parent.name or "").strip()
		# Settings sections: the grouping name holds "Section\nLabel1\nLabel2..." in the same order as its controls
		isSection = "\n" in pname or pname in _SEED or pname in _CACHE
		if parent.role == Role.GROUPING and isSection:
			if self._labelControl(obj, name, pname):
				return
		elif parent.role == Role.PANE and getattr(obj, "windowClassName", "") == "FLUTTERVIEW":
			if self._labelControl(obj, name, None):
				return
		if name:
			return
		# Unnamed check box/button right after a text (e.g. "Advanced settings")
		try:
			prev = obj.previous
		except Exception:
			prev = None
		if role == Role.CHECKBOX:
			if prev is not None and prev.role == Role.STATICTEXT and (prev.name or "").strip():
				obj.name = prev.name.strip().split("\n")[0]
			return
		# Tooltip text sits on the wrapping grouping, not the button itself
		if parent.role == Role.GROUPING and pname and not isSection:
			obj.name = pname
			return
		siblings = _children(parent)
		# Big lists (e.g. Settings) make sibling checks slow: skip them
		if len(siblings) > 8:
			return
		# Receive tab: unnamed corner buttons (history + info) at the top right
		cornerBtns = [s for s in siblings if s.role == Role.BUTTON and not (s.name or "").strip()]
		hasGroup = any(s.role == Role.GROUPING for s in siblings)
		if hasGroup and len(siblings) <= 4 and cornerBtns and all(_top(b) == _top(obj) for b in cornerBtns):
			cornerBtns.sort(key=_left)
			if len(cornerBtns) >= 2 and _left(obj) == _left(cornerBtns[0]):
				obj.name = L_HISTORY
			else:
				obj.name = L_INFO
			return
		# Fallback: describe the button by the closest text before it
		prevText = None
		for s in siblings:
			if _left(s) == _left(obj) and _top(s) == _top(obj):
				break
			if s.role == Role.STATICTEXT and (s.name or "").strip():
				prevText = s.name.strip().split("\n")[0]
		if prevText:
			obj.name = L_NEXT % prevText

	def _labelControl(self, obj, name, pname):
		ctl = (Role.BUTTON, Role.CHECKBOX)

		def code(o):
			if o.role == Role.CHECKBOX:
				return "c"
			return "B" if (o.name or "").strip() else "b"

		# Look at neighbouring controls (more reliable than parent.children in LocalSend)
		before = []
		p = obj.previous
		while p is not None and p.role in ctl and len(before) < 12:
			before.insert(0, code(p))
			p = p.previous
		after = []
		n = obj.next
		while n is not None and n.role in ctl and len(after) < 12:
			after.append(code(n))
			n = n.next
		sig = "".join(before) + code(obj) + "".join(after)
		total = len(sig)
		idx = len(before)
		labels = []
		title = None
		if pname:
			parts = pname.split("\n")
			title = parts[0].strip()
			for l in parts[1:]:
				l = l.strip()
				if not l or l.endswith("!"):
					continue  # empty or warning text, not a control label
				if ". " in l:
					l = l.split(". ")[0]
				labels.append(l)
		else:
			title = _SIGS.get(sig)
			if not title:
				return False
		if title and len(labels) == total:
			_CACHE[title] = labels
		else:
			known = _CACHE.get(title) or _SEED.get(title)
			if known and len(known) in (total, total - 1):
				labels = known
			elif len(labels) != total - 1:
				return False
		if not labels:
			return False
		extra = total - len(labels)
		if extra == 0:
			label = labels[idx]
		elif extra == 1:
			if idx > 1:
				label = labels[idx - 1]
			elif idx == 0:
				label = labels[0] + " - " + (L_START if "(" in labels[0] else L_RESTART)
			else:
				label = labels[0] + " - " + L_STOP
		else:
			return False
		obj.name = "%s: %s" % (label, name) if name and obj.role == Role.BUTTON else label
		return True

	# ---------- helpers for scripts ----------

	def _root(self):
		fg = api.getForegroundObject()
		if fg and fg.appModule is self:
			return fg
		return None

	def _navTabs(self):
		root = self._root()
		if not root:
			return []
		tabs = [o for o in _walk(root, maxDepth=14) if o.role == Role.TAB]
		return sorted(tabs, key=_top)

	def _goTab(self, index):
		tabs = self._navTabs()
		if len(tabs) <= index:
			ui.message(_t("Tab not found", "لم أجد التبويب"))
			return
		_clickObj(tabs[index])
		ui.message(tabs[index].name)

	def _toolbarGroups(self):
		"""Named groupings that wrap icon buttons (Search devices, Manual sending, Favorites)."""
		root = self._root()
		if not root:
			return []
		groups = [
			o for o in _walk(root, maxDepth=14)
			if o.role == Role.GROUPING and (o.name or "").strip() and "\n" not in (o.name or "")
			and any(c.role == Role.BUTTON for c in _children(o))
		]
		return sorted(groups, key=_left)

	@script(description=_t("Go to the Receive tab", "الانتقال إلى تبويب الاستلام"), category=CAT, gesture="kb:alt+1")
	def script_tabReceive(self, gesture):
		self._goTab(0)

	@script(description=_t("Go to the Send tab", "الانتقال إلى تبويب الإرسال"), category=CAT, gesture="kb:alt+2")
	def script_tabSend(self, gesture):
		self._goTab(1)

	@script(description=_t("Go to the Settings tab", "الانتقال إلى تبويب الإعدادات"), category=CAT, gesture="kb:alt+3")
	def script_tabSettings(self, gesture):
		self._goTab(2)

	@script(description=_t("Scan for nearby devices", "البحث عن الأجهزة القريبة"), category=CAT, gesture="kb:alt+r")
	def script_rescan(self, gesture):
		groups = self._toolbarGroups()
		if not groups:
			ui.message(_t("Open the Send tab first", "افتح تبويب الإرسال أولاً"))
			return
		btn = [c for c in _children(groups[0]) if c.role == Role.BUTTON][0]
		_clickObj(btn)
		ui.message(groups[0].name)

	@script(description=_t("Open the send mode menu", "فتح قائمة وضع الإرسال"), category=CAT, gesture="kb:alt+m")
	def script_sendMode(self, gesture):
		groups = self._toolbarGroups()
		if not groups:
			ui.message(_t("Open the Send tab first", "افتح تبويب الإرسال أولاً"))
			return
		last = groups[-1]
		loc = last.location
		# The send-mode button is not exposed to NVDA; it sits right after the last icon button.
		_clickAt(loc.left + loc.width * 1.5, loc.top + loc.height / 2)
		ui.message(_t("Send mode", "وضع الإرسال"))
