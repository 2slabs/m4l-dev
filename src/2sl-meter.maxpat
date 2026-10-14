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
			820.0,
			520.0
		],
		"openinpresentation": 1,
		"devicewidth": 150.0,
		"boxes": [
			{
				"box": {
					"id": "in",
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
					"id": "out",
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
						460.0,
						60.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "pkL",
					"maxclass": "newobj",
					"text": "peakamp~ 30",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						150.0,
						80.0,
						80.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "pkR",
					"maxclass": "newobj",
					"text": "peakamp~ 30",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						250.0,
						80.0,
						80.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "pkPak",
					"maxclass": "newobj",
					"text": "pak 0. 0.",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						150.0,
						115.0,
						100.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "pkMax",
					"maxclass": "newobj",
					"text": "maximum",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						150.0,
						145.0,
						60.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "pkPre",
					"maxclass": "newobj",
					"text": "prepend peak",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						150.0,
						175.0,
						85.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "avL",
					"maxclass": "newobj",
					"text": "average~ 2205 rms",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"signal"
					],
					"patching_rect": [
						360.0,
						80.0,
						110.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "avR",
					"maxclass": "newobj",
					"text": "average~ 2205 rms",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"signal"
					],
					"patching_rect": [
						490.0,
						80.0,
						110.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "snL",
					"maxclass": "newobj",
					"text": "snapshot~ 30",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						360.0,
						115.0,
						80.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "snR",
					"maxclass": "newobj",
					"text": "snapshot~ 30",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"float"
					],
					"patching_rect": [
						490.0,
						115.0,
						80.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "rmsPak",
					"maxclass": "newobj",
					"text": "pak 0. 0.",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						360.0,
						145.0,
						100.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "rmsPre",
					"maxclass": "newobj",
					"text": "prepend rms",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						360.0,
						175.0,
						80.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "js",
					"maxclass": "newobj",
					"text": "js 2sl-meter.js",
					"numinlets": 1,
					"numoutlets": 5,
					"outlettype": [
						"",
						"",
						"",
						"",
						""
					],
					"patching_rect": [
						150.0,
						240.0,
						230.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "lb",
					"maxclass": "newobj",
					"text": "loadbang",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					],
					"patching_rect": [
						620.0,
						200.0,
						60.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "lbMsg",
					"maxclass": "message",
					"text": "loadbang",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						620.0,
						225.0,
						60.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "peakBox",
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
						150.0,
						300.0,
						60.0,
						15.0
					],
					"presentation": 1,
					"presentation_rect": [
						62.0,
						86.0,
						80.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Peak Hold",
							"parameter_shortname": "Peak",
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
					"id": "rmsBox",
					"maxclass": "live.numbox",
					"varname": "rms",
					"parameter_enable": 1,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"float"
					],
					"patching_rect": [
						260.0,
						300.0,
						60.0,
						15.0
					],
					"presentation": 1,
					"presentation_rect": [
						62.0,
						104.0,
						80.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "RMS",
							"parameter_shortname": "RMS",
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
					"id": "winBox",
					"maxclass": "live.numbox",
					"varname": "window",
					"parameter_enable": 1,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"float"
					],
					"patching_rect": [
						620.0,
						120.0,
						50.0,
						15.0
					],
					"presentation": 1,
					"presentation_rect": [
						62.0,
						42.0,
						80.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Window",
							"parameter_shortname": "Window",
							"parameter_type": 1,
							"parameter_mmin": 1.0,
							"parameter_mmax": 30.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								5.0
							],
							"parameter_unitstyle": 0
						}
					}
				}
			},
			{
				"box": {
					"id": "winPre",
					"maxclass": "newobj",
					"text": "prepend length",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						620.0,
						150.0,
						90.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "resetBtn",
					"maxclass": "live.text",
					"varname": "measure",
					"text": "measure",
					"texton": "measure",
					"mode": 0,
					"parameter_enable": 1,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						""
					],
					"patching_rect": [
						450.0,
						200.0,
						44.0,
						15.0
					],
					"presentation": 1,
					"presentation_rect": [
						8.0,
						62.0,
						134.0,
						18.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Measure",
							"parameter_shortname": "Measure",
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
					"id": "resetTrig",
					"maxclass": "newobj",
					"text": "t b",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					],
					"patching_rect": [
						450.0,
						225.0,
						30.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "resetMsg",
					"maxclass": "message",
					"text": "measure",
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						450.0,
						250.0,
						40.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "status",
					"maxclass": "comment",
					"text": "set target, press measure",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						380.0,
						300.0,
						160.0,
						20.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						142.0,
						142.0,
						20.0
					]
				}
			},
			{
				"box": {
					"id": "title",
					"maxclass": "live.comment",
					"text": "2sl meter",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						700.0,
						30.0,
						80.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						4.0,
						140.0,
						18.0
					]
				}
			},
			{
				"box": {
					"id": "lPeak",
					"maxclass": "live.comment",
					"text": "peak",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						700.0,
						60.0,
						50.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						84.0,
						52.0,
						18.0
					]
				}
			},
			{
				"box": {
					"id": "lRms",
					"maxclass": "live.comment",
					"text": "rms",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						700.0,
						85.0,
						50.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						102.0,
						52.0,
						18.0
					]
				}
			},
			{
				"box": {
					"id": "lWin",
					"maxclass": "live.comment",
					"text": "window s",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						700.0,
						110.0,
						60.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						40.0,
						56.0,
						18.0
					]
				}
			},
			{
				"box": {
					"id": "targetBox",
					"maxclass": "live.numbox",
					"varname": "target",
					"parameter_enable": 1,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"float"
					],
					"patching_rect": [
						700.0,
						200.0,
						60.0,
						15.0
					],
					"presentation": 1,
					"presentation_rect": [
						62.0,
						24.0,
						80.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "Target",
							"parameter_shortname": "Target",
							"parameter_type": 0,
							"parameter_mmin": -24.0,
							"parameter_mmax": 0.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								-6.0
							],
							"parameter_unitstyle": 4
						}
					}
				}
			},
			{
				"box": {
					"id": "targetPre",
					"maxclass": "newobj",
					"text": "prepend target",
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						""
					],
					"patching_rect": [
						700.0,
						225.0,
						90.0,
						22.0
					]
				}
			},
			{
				"box": {
					"id": "lTarget",
					"maxclass": "live.comment",
					"text": "target",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						700.0,
						135.0,
						50.0,
						18.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						22.0,
						52.0,
						18.0
					]
				}
			},
			{
				"box": {
					"id": "change",
					"maxclass": "comment",
					"text": "change: \u2013",
					"numinlets": 1,
					"numoutlets": 0,
					"patching_rect": [
						380.0,
						330.0,
						160.0,
						20.0
					],
					"presentation": 1,
					"presentation_rect": [
						6.0,
						122.0,
						142.0,
						20.0
					]
				}
			},
			{
				"box": {
					"id": "stateBox",
					"maxclass": "live.numbox",
					"varname": "state",
					"parameter_enable": 1,
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"float"
					],
					"patching_rect": [
						560.0,
						330.0,
						50.0,
						15.0
					],
					"saved_attribute_attributes": {
						"valueof": {
							"parameter_longname": "State",
							"parameter_shortname": "State",
							"parameter_type": 1,
							"parameter_mmin": 0.0,
							"parameter_mmax": 3.0,
							"parameter_initial_enable": 1,
							"parameter_initial": [
								0.0
							],
							"parameter_unitstyle": 0
						}
					}
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"source": [
						"in",
						0
					],
					"destination": [
						"out",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"in",
						1
					],
					"destination": [
						"out",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"in",
						0
					],
					"destination": [
						"pkL",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"in",
						1
					],
					"destination": [
						"pkR",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"pkL",
						0
					],
					"destination": [
						"pkPak",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"pkR",
						0
					],
					"destination": [
						"pkPak",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"pkPak",
						0
					],
					"destination": [
						"pkMax",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"pkMax",
						0
					],
					"destination": [
						"pkPre",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"pkPre",
						0
					],
					"destination": [
						"js",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"in",
						0
					],
					"destination": [
						"avL",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"in",
						1
					],
					"destination": [
						"avR",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"avL",
						0
					],
					"destination": [
						"snL",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"avR",
						0
					],
					"destination": [
						"snR",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"snL",
						0
					],
					"destination": [
						"rmsPak",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"snR",
						0
					],
					"destination": [
						"rmsPak",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rmsPak",
						0
					],
					"destination": [
						"rmsPre",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rmsPre",
						0
					],
					"destination": [
						"js",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"js",
						0
					],
					"destination": [
						"peakBox",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"js",
						1
					],
					"destination": [
						"rmsBox",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"js",
						2
					],
					"destination": [
						"status",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"winBox",
						0
					],
					"destination": [
						"winPre",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"winPre",
						0
					],
					"destination": [
						"js",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"resetBtn",
						0
					],
					"destination": [
						"resetTrig",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"resetTrig",
						0
					],
					"destination": [
						"resetMsg",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"resetMsg",
						0
					],
					"destination": [
						"js",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"lb",
						0
					],
					"destination": [
						"lbMsg",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"lbMsg",
						0
					],
					"destination": [
						"js",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"targetBox",
						0
					],
					"destination": [
						"targetPre",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"targetPre",
						0
					],
					"destination": [
						"js",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"js",
						3
					],
					"destination": [
						"change",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"js",
						4
					],
					"destination": [
						"stateBox",
						0
					]
				}
			}
		]
	}
}