document.addEventListener("DOMContentLoaded", function () {
  var btn = document.getElementById("copy-install");
  if (!btn) return;
  btn.addEventListener("click", function () {
    var text = "git clone https://github.com/n9w6vh4vqr-hub/codebase-grounding.git\ncp -r codebase-grounding ~/.claude/skills/codebase-grounding";
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function () {
        var original = btn.textContent;
        btn.textContent = "Copiado";
        setTimeout(function () { btn.textContent = original; }, 1500);
      });
    }
  });
});
