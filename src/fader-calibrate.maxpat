{
	"patcher": {
		"fileversion": 1,
		"appversion": { "major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1 },
		"rect": [ 100.0, 100.0, 640.0, 400.0 ],
		"openinpresentation": 1,
		"devicewidth": 0.0,
		"boxes": [
			{ "box": { "id": "obj-1", "maxclass": "newobj", "text": "plugin~", "numinlets": 2, "numoutlets": 2, "outlettype": [ "signal", "signal" ], "patching_rect": [ 30.0, 30.0, 60.0, 22.0 ] } },
			{ "box": { "id": "obj-2", "maxclass": "newobj", "text": "plugout~", "numinlets": 2, "numoutlets": 2, "outlettype": [ "signal", "signal" ], "patching_rect": [ 30.0, 90.0, 60.0, 22.0 ] } },
			{ "box": { "id": "obj-3", "maxclass": "newobj", "text": "live.thisdevice", "numinlets": 1, "numoutlets": 3, "outlettype": [ "bang", "int", "int" ], "patching_rect": [ 160.0, 30.0, 90.0, 22.0 ] } },
			{ "box": { "id": "obj-4", "maxclass": "newobj", "text": "deferlow", "numinlets": 1, "numoutlets": 1, "outlettype": [ "" ], "patching_rect": [ 160.0, 60.0, 60.0, 22.0 ] } },
			{ "box": { "id": "obj-5", "maxclass": "newobj", "text": "js fader-calibrate.js", "numinlets": 1, "numoutlets": 1, "outlettype": [ "" ], "patching_rect": [ 160.0, 90.0, 130.0, 22.0 ] } },
			{ "box": { "id": "obj-6", "maxclass": "message", "text": "", "numinlets": 2, "numoutlets": 1, "outlettype": [ "" ], "patching_rect": [ 160.0, 130.0, 120.0, 22.0 ], "presentation": 1, "presentation_rect": [ 8.0, 30.0, 120.0, 22.0 ] } },
			{ "box": { "id": "obj-7", "maxclass": "newobj", "text": "prepend set", "numinlets": 1, "numoutlets": 1, "outlettype": [ "" ], "patching_rect": [ 300.0, 110.0, 80.0, 22.0 ] } },
			{ "box": { "id": "obj-8", "maxclass": "comment", "text": "fader calibration", "numinlets": 1, "numoutlets": 0, "patching_rect": [ 300.0, 30.0, 120.0, 20.0 ], "presentation": 1, "presentation_rect": [ 8.0, 6.0, 140.0, 20.0 ] } }
		],
		"lines": [
			{ "patchline": { "source": [ "obj-1", 0 ], "destination": [ "obj-2", 0 ] } },
			{ "patchline": { "source": [ "obj-1", 1 ], "destination": [ "obj-2", 1 ] } },
			{ "patchline": { "source": [ "obj-3", 0 ], "destination": [ "obj-4", 0 ] } },
			{ "patchline": { "source": [ "obj-4", 0 ], "destination": [ "obj-5", 0 ] } },
			{ "patchline": { "source": [ "obj-5", 0 ], "destination": [ "obj-7", 0 ] } },
			{ "patchline": { "source": [ "obj-7", 0 ], "destination": [ "obj-6", 0 ] } }
		]
	}
}
