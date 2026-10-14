// Writes Live's fader curve (internal value -> displayed dB) for the track this device is on.
// Output: ~/m4l-dev/fader-curve.tsv. Run once, then delete the device.
autowatch = 1;
outlets = 1;

function bang() {
  var api = new LiveAPI("this_device canonical_parent mixer_device volume");
  if (!api || api.id == 0) { post("fader-calibrate: no mixer volume found\n"); outlet(0, "error"); return; }
  var lines = ["value\tdisplay"];
  for (var i = 0; i <= 2000; i++) {
    var v = i / 2000;
    var s = api.call("str_for_value", v);
    lines.push(v.toFixed(4) + "\t" + s);
  }
  var path = "/Users/codysmith/m4l-dev/fader-curve.tsv";
  var f = new File(path, "write", "TEXT");
  if (!f.isopen) { post("fader-calibrate: couldn't open " + path + "\n"); outlet(0, "error"); return; }
  f.eof = 0;
  f.writestring(lines.join("\n") + "\n");
  f.close();
  post("fader-calibrate: wrote " + (lines.length - 1) + " rows to " + path + "\n");
  outlet(0, "done");
}
