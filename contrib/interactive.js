var popup;
var ofs_x = 16, ofs_y = 16;

function init_popup() {
    popup = document.createElement('div');
    document.body.appendChild(popup);
    popup.className = 'popup';
    popup.style.display = 'none';
    popup.style.position = 'absolute';
}

function show_popup(evt, content) {
    popup.innerHTML = content;
    popup.style.display = 'block';
    popup.style.left = (evt[0].clientX + ofs_x) + 'px';
    popup.style.top = (evt[0].clientY + ofs_y) + 'px';
}

function hide_popup(evt) {
    popup.style.display = 'none';
}
