'''
The envi.qt.html module contains the HTML template and javascript
code used by the renderers (which are based on QtWebKit)
'''

template = '''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:svg="http://www.w3.org/2000/svg" id="mainhtml">
<head></head>

<style type="text/css">

body {
    color: #00ff00;
    background-color: #000000;
    font: 10pt Monospace;
}

div.memcanvas {
    color: #00ff00;
    background-color: #000000;
}

div.codeblock {
    color: #00ff00;
    background-color: #000000;
    border: 2px solid #00ff00;
    display: inline-block;
}

div.codeblock:hover {
    border: 2px solid #ff0000;
}

mnemonic {
    color: #ffff00;
    background-color: #000000;
}

va {
    color: #4040ff;
    background-color: #000000;
}

va:hover {
    font-weight: 900;
}

name {
    color: #00ff00;
    background-color: #000000;
}

registers {
    color: #ff0000;
    background-color: #000000;
}

</style>

<style type="text/css" id="cmapstyle">
</style>

<script language="javascript">
<![CDATA[

function colorCssClass(seltext, color, bgcolor) {

    var i = 0;
    var myrules = document.styleSheets[0].cssRules;

    seltext = seltext.toLowerCase();

    // Attempt to find the matching rule.
    for ( i = 0; i < myrules.length; i++) {

        if( myrules[i].selectorText.toLowerCase() == seltext) {
            myrules[i].style.color = color;
            myrules[i].style.backgroundColor = bgcolor;
            return;
        }

    }

    // If we get here, there is no rule for just that tag yet...
    var rule = seltext + " { color: " + color + "; background-color: " + bgcolor + "; }";
    document.styleSheets[0].insertRule(rule, 0);
}

function getStyleProp(elem, cssprop) {
    return document.defaultView.getComputedStyle(elem, "").getPropertyValue(cssprop);
}

function swapColors(elem) {
    var cssname = elem.tagName + '.' + elem.className;
    var fgcolor = getStyleProp(elem, 'color');
    var bgcolor = getStyleProp(elem, 'background-color');
    colorCssClass(cssname, bgcolor, fgcolor);
}

var curname = null;
function nameclick(elem) {
    if (curname != null) {
        swapColors(curname);
    }
    swapColors(elem);
    curname = elem;
}

var curva = null;
function vaclick(elem) {
    if (curva != null) {
        swapColors(curva);
    }
    swapColors(elem);
    curva = elem;

    var vastr = elem.className.split("_", 2)[1];
    vnav._jsSetCurVa(vastr)
}

function vagoto(elem) {
    var vastr = elem.className.split("_", 2)[1];
    vnav._jsGotoExpr(vastr);
}


]]>
</script>

<body id="vbody" width="999px">

<div class="memcanvas" id="memcanvas">
</div>

</body>

</html>
'''

