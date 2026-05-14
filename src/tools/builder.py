"""Base class and shared helpers for all sport-specific workout builders."""
import auth

_REPEAT_STEP_TYPE = {"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6}
_COND_ITER        = {
    "conditionTypeId": 7, "conditionTypeKey": "iterations",
    "displayOrder": 7, "displayable": False,
}


def repeat_group(step_order: int, n: int, steps: list, *, skip_last_rest: bool = True) -> dict:
    return {
        "type":               "RepeatGroupDTO",
        "stepOrder":          step_order,
        "stepType":           _REPEAT_STEP_TYPE,
        "childStepId":        1,
        "numberOfIterations": n,
        "endCondition":       _COND_ITER,
        "endConditionValue":  float(n),
        "skipLastRestStep":   skip_last_rest,
        "smartRepeat":        False,
        "workoutSteps":       steps,
    }


class WorkoutBuilder:
    """Base class for sport-specific workout builders.

    Subclasses implement build_payload(spec) -> dict.
    create() and update() are sport-agnostic and use upload_workout for all sports.
    """

    def build_payload(self, spec: dict) -> dict:
        raise NotImplementedError

    def create(self, spec: dict) -> dict:
        payload    = self.build_payload(spec)
        result     = auth.get_client().upload_workout(payload)
        workout_id = result.get("workoutId") or result.get("workout", {}).get("workoutId")
        return {"workoutId": workout_id, "name": spec.get("name", "Workout")}

    def update(self, workout_id: str, spec: dict) -> dict:
        payload              = self.build_payload(spec)
        payload["workoutId"] = int(workout_id)
        client               = auth.get_client()
        client.client.put("connectapi", f"/workout-service/workout/{workout_id}", json=payload)
        return {"workoutId": int(workout_id), "name": spec.get("name", "Workout"), "updated": True}
