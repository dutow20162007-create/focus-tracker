import os

from qfluentwidgets import (
    BoolValidator,
    ConfigItem,
    OptionsConfigItem,
    OptionsValidator,
    QConfig,
    RangeConfigItem,
    RangeValidator,
    qconfig,
)

from .database import DATA_DIR

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")


class AppConfig(QConfig):
    theme = OptionsConfigItem("Appearance", "Theme", "Dark", OptionsValidator(["Dark", "Light"]))
    language = OptionsConfigItem("General", "Language", "ru", OptionsValidator(["ru", "en"]))

    trackingEnabled = ConfigItem("Tracking", "Enabled", True, BoolValidator())
    pollInterval = RangeConfigItem("Tracking", "PollInterval", 2, RangeValidator(1, 10))
    idleThreshold = RangeConfigItem("Tracking", "IdleThresholdMin", 3, RangeValidator(1, 30))

    pomodoroWork = RangeConfigItem("Pomodoro", "WorkMin", 25, RangeValidator(5, 90))
    pomodoroBreak = RangeConfigItem("Pomodoro", "BreakMin", 5, RangeValidator(1, 30))
    pomodoroLongBreak = RangeConfigItem("Pomodoro", "LongBreakMin", 15, RangeValidator(5, 60))
    pomodoroRounds = RangeConfigItem("Pomodoro", "Rounds", 4, RangeValidator(2, 8))

    notifications = ConfigItem("Notifications", "Enabled", True, BoolValidator())
    distractionAlerts = ConfigItem("Notifications", "DistractionAlerts", True, BoolValidator())
    distractionLimitMin = RangeConfigItem(
        "Notifications", "DistractionLimitMin", 15, RangeValidator(1, 120)
    )

    autostart = ConfigItem("General", "Autostart", False, BoolValidator())
    minimizeToTray = ConfigItem("General", "MinimizeToTray", True, BoolValidator())


cfg = AppConfig()
qconfig.load(CONFIG_PATH, cfg)
