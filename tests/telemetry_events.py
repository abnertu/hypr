# pyright: standard
"""Report each unittest case to the telemetry runner.

The runner sets TELEMETRY_EVENTS=1 in the child environment. Each event is one
stdout line: the record separator byte, "telemetry ", and a JSON object.
"""

import json
import os
import sys
import unittest

PREFIX = "\x1etelemetry "


def emit(event):
    sys.stdout.write(PREFIX + json.dumps(event) + "\n")
    sys.stdout.flush()


class TelemetryResult(unittest.TextTestResult):
    """Emit test_start and test_end events next to the normal text report."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = os.environ.get("TELEMETRY_EVENTS") == "1"
        self.status = "pass"

    def startTest(self, test):
        super().startTest(test)
        self.status = "pass"
        if self.enabled:
            emit({"event": "test_start", "name": self.name(test)})

    def stopTest(self, test):
        if self.enabled:
            emit({"event": "test_end", "name": self.name(test), "status": self.status})
        super().stopTest(test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.status = "fail"

    def addError(self, test, err):
        super().addError(test, err)
        self.status = "error"

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.status = "fail"

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None and self.status == "pass":
            self.status = "fail" if issubclass(err[0], test.failureException) else "error"

    @staticmethod
    def name(test):
        return test.id().removeprefix("__main__.")


def main():
    """Run the calling module's tests with telemetry events."""
    unittest.main(testRunner=unittest.TextTestRunner(resultclass=TelemetryResult))
