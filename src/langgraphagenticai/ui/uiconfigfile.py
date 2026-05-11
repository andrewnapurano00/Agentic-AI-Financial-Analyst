import configparser
import os


class Config:
    def __init__(self, config_file=None):
        if config_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(current_dir, "uiconfigfile.ini")

        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.PAGE_TITLE = self.config.get("DEFAULT", "PAGE_TITLE", fallback="Agentic AI Financial Analyst")
        self.LLM_OPTIONS = self._get_list("LLM", "LLM_OPTIONS")
        self.OPENAI_MODEL_OPTIONS = self._get_list("OPENAI", "OPENAI_MODEL_OPTIONS")
        self.USECASE_OPTIONS = self._get_list("USECASE", "USECASE_OPTIONS")

    def _get_list(self, section, option):
        value = self.config.get(section, option, fallback="")
        return [item.strip() for item in value.split(",") if item.strip()]
