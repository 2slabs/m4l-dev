{
	"patcher": {
		"fileversion": 1,
		"appversion": {
			"major": 9,
			"minor": 1,
			"revision": 5,
			"architecture": "x64",
			"modernui": 1
		},
		"rect": [
			100.0,
			100.0,
			760.0,
			480.0
		],
		"openinpresentation": 1,
		"devicewidth": 132.0,
		"boxes": [
			{
				"box": {
					"id": "obj-1",
					"maxclass": "newobj",
					"text": "plugin~",
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"signal",
						"signal"
					],
					"patching_rect": [
						30.0,
						30.0,
						60.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-2",
					"maxclass": "newobj",
					"text": "plugout~",
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"signal",
						"signal"
					],
					"patching_rect": [
						30.0,
						380.0,
						60.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-3",
					"maxclass": "newobj",
					"text": "peakamp~ 30",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						160.0,
						80.0,
						80.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-4",
					"maxclass": "newobj",
					"text": "peakamp~ 30",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						260.0,
						80.0,
						80.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-5",
					"maxclass": "newobj",
					"text": "pak 0. 0.",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						160.0,
						120.0,
						100.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-6",
					"maxclass": "newobj",
					"text": "maximum",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						160.0,
						150.0,
						60.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-7",
					"maxclass": "newobj",
					"text": "js 2sl-meter.js",
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						""
					],
					"patching_rect": [
						160.0,
						190.0,
						110.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-8",
					"maxclass": "live.numbox",
					"varname": "peak_hold",
					"parameter_enable": 1,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"float"
					],
					"patching_rect": [
						160.0,
						240.0,
						60.0,
						15.0
					],
					"presentation": 1,
					"presentation_rect": [
						8.0,
						44.0,
						116.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Peak Hold",
							"parameter_shortname": "Peak Hold",
							"parameter_type": 0,
							"parameter_mmin": -70.0,
							"parameter_mmax": 24.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								-70.0
							],
							"parameter_unitstyle": 4
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-10",
					"maxclass": "flonum",
					"format": 6,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					],
					"parameter_enable": 0,
					"patching_rect": [
						290.0,
						240.0,
						60.0,
						22.0
					],
					"presentation": 1,
					"presentation_rect": [
						8.0,
						84.0,
						116.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-11",
					"maxclass": "live.text",
					"varname": "reset",
					"text": "reset",
					"texton": "reset",
					"mode": 0,
					"parameter_enable": 1,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						""
					],
					"patching_rect": [
						400.0,
						120.0,
						44.0,
						15.0
					],
					"presentation": 1,
					"presentation_rect": [
						8.0,
						120.0,
						116.0,
						18.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Reset",
							"parameter_shortname": "Reset",
							"parameter_type": 2,
							"parameter_enum": [
								"off",
								"on"
							],
							"parameter_mmax": 1
						}
					}
				}
			},
			{
				"box": {
					"id": "obj-12",
					"maxclass": "newobj",
					"text": "sel 1",
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					],
					"patching_rect": [
						400.0,
						150.0,
						40.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-13",
					"maxclass": "message",
					"text": "reset",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						400.0,
						180.0,
						40.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "obj-14",
					"maxclass": "live.comment",
					"text": "2sl meter",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						500.0,
						60.0,
						80.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						6.0,
						120.0,
						18.0
					]
				}
			},
			{
				"box": {
					"id": "obj-15",
					"maxclass": "live.comment",
					"text": "peak hold (pre-limiter)",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						500.0,
						90.0,
						140.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						26.0,
						124.0,
						18.0
					]
				}
			},
			{
				"box": {
					"id": "obj-16",
					"maxclass": "live.comment",
					"text": "now",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						500.0,
						120.0,
						60.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						66.0,
						60.0,
						18.0
					]
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"source": [
						"obj-1",
						0
					],
					"destination": [
						"obj-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-1",
						1
					],
					"destination": [
						"obj-2",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-1",
						0
					],
					"destination": [
						"obj-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-1",
						1
					],
					"destination": [
						"obj-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-3",
						0
					],
					"destination": [
						"obj-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-4",
						0
					],
					"destination": [
						"obj-5",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-5",
						0
					],
					"destination": [
						"obj-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-6",
						0
					],
					"destination": [
						"obj-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-7",
						0
					],
					"destination": [
						"obj-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-7",
						1
					],
					"destination": [
						"obj-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-11",
						0
					],
					"destination": [
						"obj-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-12",
						0
					],
					"destination": [
						"obj-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"obj-13",
						0
					],
					"destination": [
						"obj-7",
						0
					]
				}
			}
		]
	}
}