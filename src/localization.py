import json

_localization = dict()

def load(lang="ru_RU"):
	global _localization
	try:
		with open(f"lang/{lang}.json", "r", encoding="utf-8") as file:
			_localization = json.load(file)
		print(f"Localization {lang} loaded successfully.")
	except FileNotFoundError:
		print(f"Localization file {lang}.json was not found.")
		if _localization == dict() and lang != "ru_RU":
			load()

def get(string_identifier: str):
	if string_identifier in _localization:
		return _localization[string_identifier]
	if _localization == dict():
		print("Localization was not loaded!")
	print(f"string identifier {string_identifier} does not exist!")
	return f"Identifier does not exist: {string_identifier}"
