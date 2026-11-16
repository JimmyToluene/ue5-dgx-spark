"""Drive the running Unreal editor through its Remote Control HTTP API (127.0.0.1:30010).

    import rc
    rc.call(obj, func, **params)      -> ReturnValue (or the whole reply when there is none)
    rc.cmd("console command")
    rc.get(obj, prop) / rc.set(obj, prop, value)
"""
import json
import urllib.request

HOST = "http://127.0.0.1:30010"
EAS = "/Script/UnrealEd.Default__EditorActorSubsystem"
UES = "/Script/UnrealEd.Default__UnrealEditorSubsystem"
LES = "/Script/LevelEditor.Default__LevelEditorSubsystem"
KSL = "/Script/Engine.Default__KismetSystemLibrary"
EAL = "/Script/EditorScriptingUtilities.Default__EditorAssetLibrary"
SMES = "/Script/StaticMeshEditor.Default__StaticMeshEditorSubsystem"


class RCError(RuntimeError):
    pass


def _put(route, body, timeout=600):
    req = urllib.request.Request(HOST + route, data=json.dumps(body).encode(), method="PUT",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode()
    except urllib.error.HTTPError as e:
        raise RCError("%s %s -> %s %s" % (route, json.dumps(body)[:300], e.code, e.read().decode()[:400]))
    out = json.loads(txt) if txt.strip() else {}
    if isinstance(out, dict) and "errorMessage" in out:
        raise RCError("%s -> %s" % (json.dumps(body)[:300], out["errorMessage"]))
    return out


def call(obj, func, _transaction=True, **params):
    out = _put("/remote/object/call", {"objectPath": obj, "functionName": func, "parameters": params,
                                       "generateTransaction": _transaction})
    return out.get("ReturnValue", out) if isinstance(out, dict) else out


def get(obj, prop=None):
    body = {"objectPath": obj, "access": "READ_ACCESS"}
    if prop:
        body["propertyName"] = prop
    out = _put("/remote/object/property", body)
    return out.get(prop, out) if prop else out


def set(obj, prop, value):
    return _put("/remote/object/property", {"objectPath": obj, "propertyName": prop, "access": "WRITE_TRANSACTION_ACCESS",
                                            "propertyValue": {prop: value}})


def world():
    return call(UES, "GetEditorWorld")


def cmd(command):
    return call(KSL, "ExecuteConsoleCommand", WorldContextObject=world(), Command=command)


def vec(x, y, z):
    return {"X": x, "Y": y, "Z": z}


def rot(pitch, yaw, roll=0.0):
    return {"Pitch": pitch, "Yaw": yaw, "Roll": roll}


def spawn_mesh(mesh, loc, scale=(1, 1, 1), rotation=(0, 0, 0), material=None, label=None):
    a = call(EAS, "SpawnActorFromObject", ObjectToUse=mesh, Location=vec(*loc), Rotation=rot(*rotation))
    call(a, "SetActorScale3D", NewScale3D=vec(*scale))
    if material:
        call(a + ".StaticMeshComponent0", "SetMaterial", ElementIndex=0, Material=material)
    if label:
        call(a, "SetActorLabel", NewActorLabel=label)
    return a


def spawn_class(cls, loc, rotation=(0, 0, 0), label=None):
    a = call(EAS, "SpawnActorFromClass", ActorClass=cls, Location=vec(*loc), Rotation=rot(*rotation))
    if label:
        call(a, "SetActorLabel", NewActorLabel=label)
    return a


def camera(loc, rotation):
    return call(UES, "SetLevelViewportCameraInfo", CameraLocation=vec(*loc), CameraRotation=rot(*rotation))
