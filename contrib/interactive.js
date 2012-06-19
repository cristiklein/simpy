var popup;
var ofs_x = 16, ofs_y = 16;

function init_popup() {
    popup = document.createElement('div');
    document.body.appendChild(popup);
    popup.className = 'popup';
    popup.style.display = 'none';
    popup.style.position = 'absolute';
}

function show_popup(evt, content, filename, lineno) {
    popup.innerHTML = content;
    popup.style.display = 'block';
    popup.style.left = (evt[0].clientX + ofs_x) + 'px';
    popup.style.top = (evt[0].clientY + ofs_y) + 'px';

    if(filename == undefined || lineno == undefined) return;

    show_source(filename, lineno);
}

function hide_popup(evt) {
    popup.style.display = 'none';
    show_source();
}

var highlight_line = undefined;

function show_source(filename, lineno) {
    if(highlight_line != undefined) {
        highlight_line.className = 'hll';
        highlight_line = undefined;
    }

    if(filename == undefined) return;

    var code = document.getElementsByName('sourcecode')[0];
    for(var i = 0; i < code.childNodes.length; i++) {
        var page = code.childNodes[i];
        if(page.tagName != 'DIV') continue;
        if(page.getAttribute('name') == 'page') break;
    }
    var file = undefined;
    for(var i = 0; i < page.childNodes.length; i++) {
        var child = page.childNodes[i];
        if(child.tagName != 'DIV') continue;
        if(child.className == 'navbar') continue;
        if(child.getAttribute('name') == filename) {
            file = child;
            child.className = '';
        } else {
            child.className = 'hidden';
        }
    }

    if(lineno == undefined) return;

    highlight_line = file.getElementsByTagName('a')[lineno-1].nextSibling;
    highlight_line.className = 'hll active';
    highlight_line.scrollIntoView()
}
