{
	"patcher": {
		"fileversion": 1,
		"appversion": { "major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1 },
		"rect": [ 100.0, 100.0, 640.0, 480.0 ],
		"openinpresentation": 1,
		"default_fontsize": 12.0,
		"default_fontname": "Arial",
		"devicewidth": 0.0,
		"boxes": [
			{ "box": { "id": "obj-1", "maxclass": "newobj", "text": "plugin~", "numinlets": 2, "numoutlets": 2, "outlettype": [ "signal", "signal" ], "patching_rect": [ 40.0, 40.0, 60.0, 22.0 ] } },
			{ "box": { "id": "obj-2", "maxclass": "live.dial", "varname": "Gain", "parameter_enable": 1, "numinlets": 1, "numoutlets": 2, "outlettype": [ "", "float" ],
				"patching_rect": [ 220.0, 30.0, 44.0, 48.0 ], "presentation": 1, "presentation_rect": [ 10.0, 10.0, 44.0, 48.0 ],
				"saved_attribute_attributes": { "valueof": { "parameter_longname": "Gain", "parameter_shortname": "Gain", "parameter_type": 0,
					"parameter_mmin": -70.0, "parameter_mmax": 12.0, "parameter_initial_enable": 1, "parameter_initial": [ 0.0 ], "parameter_unitstyle": 4 } } } },
			{ "box": { "id": "obj-3", "maxclass": "newobj", "text": "dbtoa", "numinlets": 1, "numoutlets": 1, "outlettype": [ "" ], "patching_rect": [ 220.0, 90.0, 45.0, 22.0 ] } },
			{ "box": { "id": "obj-4", "maxclass": "newobj", "text": "pack f 20", "numinlets": 2, "numoutlets": 1, "outlettype": [ "" ], "patching_rect": [ 220.0, 120.0, 60.0, 22.0 ] } },
			{ "box": { "id": "obj-5", "maxclass": "newobj", "text": "line~", "numinlets": 2, "numoutlets": 2, "outlettype": [ "signal", "bang" ], "patching_rect": [ 220.0, 150.0, 40.0, 22.0 ] } },
			{ "box": { "id": "obj-6", "maxclass": "newobj", "text": "*~ 1.", "numinlets": 2, "numoutlets": 1, "outlettype": [ "signal" ], "patching_rect": [ 40.0, 190.0, 40.0, 22.0 ] } },
			{ "box": { "id": "obj-7", "maxclass": "newobj", "text": "*~ 1.", "numinlets": 2, "numoutlets": 1, "outlettype": [ "signal" ], "patching_rect": [ 120.0, 190.0, 40.0, 22.0 ] } },
			{ "box": { "id": "obj-8", "maxclass": "newobj", "text": "plugout~", "numinlets": 2, "numoutlets": 2, "outlettype": [ "signal", "signal" ], "patching_rect": [ 40.0, 240.0, 100.0, 22.0 ] } }
		],
		"lines": [
			{ "patchline": { "source": [ "obj-1", 0 ], "destination": [ "obj-6", 0 ] } },
			{ "patchline": { "source": [ "obj-1", 1 ], "destination": [ "obj-7", 0 ] } },
			{ "patchline": { "source": [ "obj-2", 0 ], "destination": [ "obj-3", 0 ] } },
			{ "patchline": { "source": [ "obj-3", 0 ], "destination": [ "obj-4", 0 ] } },
			{ "patchline": { "source": [ "obj-4", 0 ], "destination": [ "obj-5", 0 ] } },
			{ "patchline": { "source": [ "obj-5", 0 ], "destination": [ "obj-6", 1 ] } },
			{ "patchline": { "source": [ "obj-5", 0 ], "destination": [ "obj-7", 1 ] } },
			{ "patchline": { "source": [ "obj-6", 0 ], "destination": [ "obj-8", 0 ] } },
			{ "patchline": { "source": [ "obj-7", 0 ], "destination": [ "obj-8", 1 ] } }
		]
	}
}
