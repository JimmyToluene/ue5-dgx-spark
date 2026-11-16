#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
"""Build a closed test room in a new level through Remote Control: white floor/ceiling/back wall, a red and a
green side wall, two objects and one point light. No sky, so everything the light does not reach directly is
black unless global illumination works.  usage: make_lumen_room.py   (editor must be running with Remote Control)"""
import rc

AT = "/Script/AssetTools.Default__AssetToolsImpl"
MEL = "/Script/MaterialEditor.Default__MaterialEditingLibrary"
CUBE, SPHERE = "/Engine/BasicShapes/Cube.Cube", "/Engine/BasicShapes/Sphere.Sphere"


def mi(name, rgb):
    path = "/Game/Test/" + name
    obj = path + "." + name
    if not rc.call(rc.EAL, "DoesAssetExist", AssetPath=path):
        rc.call(AT, "CreateAsset", AssetName=name, PackagePath="/Game/Test", AssetClass="/Script/Engine.MaterialInstanceConstant",
                Factory="/Script/UnrealEd.Default__MaterialInstanceConstantFactoryNew")
    rc.call(MEL, "SetMaterialInstanceParent", Instance=obj, NewParent="/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")
    rc.call(MEL, "SetMaterialInstanceVectorParameterValue", Instance=obj, ParameterName="Color",
            Value={"R": rgb[0], "G": rgb[1], "B": rgb[2], "A": 1.0}, Association="GlobalParameter")   # the default sent by Remote Control is "Layer"
    rc.call(MEL, "UpdateMaterialInstance", Instance=obj)
    return obj


def main():
    rc.new_level("/Game/Test/LumenRoom")
    white, red, green, grey = mi("MI_White", (0.75, 0.75, 0.75)), mi("MI_Red", (0.8, 0.05, 0.05)), mi("MI_Green", (0.08, 0.7, 0.08)), mi("MI_Grey", (0.4, 0.4, 0.42))
    # room 8 m x 8 m x 4 m, open toward -X where the camera stands; cube mesh is 1 m
    rc.spawn_mesh(CUBE, (0, 0, -10), (8, 8, 0.2), material=white, label="Floor")
    rc.spawn_mesh(CUBE, (0, 0, 410), (8, 8, 0.2), material=white, label="Ceiling")
    rc.spawn_mesh(CUBE, (410, 0, 200), (0.2, 8.4, 4.4), material=white, label="BackWall")
    rc.spawn_mesh(CUBE, (0, -410, 200), (8, 0.2, 4.4), material=red, label="RedWall")
    rc.spawn_mesh(CUBE, (0, 410, 200), (8, 0.2, 4.4), material=green, label="GreenWall")
    # a partition that hides the back-right part of the room from the light
    rc.spawn_mesh(CUBE, (150, 120, 150), (0.3, 3.0, 3.0), material=white, label="Partition")
    rc.spawn_mesh(CUBE, (60, -180, 80), (1.6, 1.6, 1.6), rotation=(0, 25, 0), material=grey, label="Box")
    rc.spawn_mesh(SPHERE, (-80, 80, 60), (1.2, 1.2, 1.2), material=white, label="Ball")
    light = rc.spawn_class("/Script/Engine.PointLight", (-150, -150, 330), label="Lamp")
    comp = light + ".LightComponent0"
    rc.call(comp, "SetIntensityUnits", NewIntensityUnits="Candelas")
    rc.call(comp, "SetIntensity", NewIntensity=600.0)
    rc.call(comp, "SetAttenuationRadius", NewRadius=2000.0)
    rc.set(comp, "SourceRadius", 12.0)
    # fixed exposure so pictures with and without global illumination can be compared
    ppv = rc.spawn_class("/Script/Engine.PostProcessVolume", (0, 0, 200), label="FixedExposure")
    rc.set(ppv, "bUnbound", True)
    rc.set(ppv, "Settings", {"bOverride_AutoExposureMinBrightness": True, "AutoExposureMinBrightness": 1.0,
                             "bOverride_AutoExposureMaxBrightness": True, "AutoExposureMaxBrightness": 1.0,
                             "bOverride_AutoExposureBias": True, "AutoExposureBias": -3.0})
    rc.spawn_class("/Script/Engine.PlayerStart", (-700, 0, 150), label="BenchStart")   # camera for tools/bench_game.sh
    rc.camera((-1050, 0, 200), (0, 0, 0))
    rc.call(rc.LES, "SaveCurrentLevel")
    print("room built:", len(rc.call(rc.EAS, "GetAllLevelActors")), "actors")


if __name__ == "__main__":
    main()
