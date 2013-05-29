/* sirc.js */

// Global Variables

var channel = '';
var last_update = '';
var last_downdate = '';
var transition_id = 0;

// Utility

var add_process = function(xml, flag) {
    $('log', xml).each(function(i) {
        var datetime = $(this).find('datetime').text();
        var source = $(this).find('source').text();
        var message = $(this).find('message').text();
        append_log(flag, datetime, source, message);
    });
    $('ul#log').listview('refresh');
};

var append_log = function(flag, datetime, source, message) {
    var element = $('<li><div class="datetime">' + datetime_format(datetime) + '</div><div class="source">&lt;<span class="nick c-' + simple_hash(source) + '">' + html_encode(source) + '</span>&gt;</div><div class="message">' + url_detection(html_encode(message)) + '</div></li>');
    if(flag == 'downdate') {
        last_downdate = datetime;
        element.prependTo($('ul#log'));
    }else {
        if(flag != 'send') last_update = datetime;
        else element.attr('data-theme', 'b');
        element.appendTo($('ul#log')).attr('flag', flag);
    }
    if(flag != 'downdate')
        scroll(SCROLL_END, 200);
};

var datetime_format = function(datetime) {
    return datetime.substring(5, 16).replace(' ', '<br />');
};

var datetime_now = function() {
    var d = new Date();
    return d.getFullYear() + '-' + (d.getMonth() + 1) +  '-' + d.getDate() + ' ' + d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds();
};

var html_encode = function(s) {
    var e = document.createElement('div');
    e.innerText = e.textContent = s;
    s = e.innerHTML;
    delete e;
    return s.replace(/ /g, '&nbsp;');
};

var SCROLL_END = -1;
var scroll = function(pos, duration) {
    if($('#scrolling').val() == 'off') return;
    if(pos == SCROLL_END) pos = $('ul#log').height();
    $('body,html,document').animate({scrollTop: pos}, duration);
};

var simple_hash = function(s) {
    var sum = 0;
    for(var i = 0; i < s.length; i++) {
        sum += s.charCodeAt(i);
    }
    return sum % 16;
};

var trim = function(str){
    return str.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
};

var URL_PATTERN = /(((https?|ftp):\/\/)(([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)|localhost|([a-zA-Z0-9_\-]+\.)*[a-zA-Z0-9\-]+\.(com|net|org|info|biz|gov|name|edu|[a-zA-Z][a-zA-Z]))(:[0-9]+)?((\/|\?)[^ "]*[^ ,;\.:">\)])?)/g; // from dputty
var CHANNEL_PATTERN = /#([\w-]+|[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]+[\w-]*)/g;
var url_detection = function(str) {
    var replaced_str = str.replace(URL_PATTERN, '<a href="' + '$&' + '" target="_blank">' + '$&' + '</a>');
    if(replaced_str != str) return replaced_str;
    return str.replace(CHANNEL_PATTERN, '<a href="' + '$&' + '" target="_blank">' + '$&' + '</a>');
};

// Ajax Calls

var sirc_update = function() {
    if(channel == '') return false;
    $.ajax({
        type: 'GET',
        url: '/update/',
        data: 'channel=' + encodeURIComponent(channel) + '&last_update=' + encodeURIComponent(last_update) + '&transition_id=' + transition_id,
        dataType: 'xml',
        success: function(xml) {
            var result = $('result', xml);
            if(result.attr('transition_id') == transition_id) {
                if(result.attr('status') == 'flooded') {
                    sirc_join();
                }else {
                    add_process(xml, 'update');
                    $('ul#log > li[flag="send"]').remove();
                    setTimeout("sirc_update();", 500);
                }
            }
        },
        error: function(xhr) {
            //alert('update: ' + xhr.responseText);
            setTimeout("sirc_update();", 500);
            $('h1#channel').addClass('disconnected');
        }
    });
    $('h1#channel').removeClass('disconnected');
    return false;
};

var sirc_downdate = function(callback) {
    if(channel == '') return false;
    $.mobile.showPageLoadingMsg();
    $.ajax({
        type: 'GET',
        url: '/downdate/',
        data: 'channel=' + encodeURIComponent(channel) + '&last_downdate=' + encodeURIComponent(last_downdate) + '&transition_id=' + transition_id,
        dataType: 'xml',
        success: function(xml) {
            if($('result', xml).attr('transition_id') == transition_id) {
                add_process(xml, 'downdate');
                if($('log', xml).length > 0)
                    $('<li><a>more...</a></li>').click(function() { $(this).remove(); return sirc_downdate(); }).prependTo($('ul#log'));
                $('ul#log').listview('refresh');
                if(callback) callback();
                $.mobile.hidePageLoadingMsg();
            }
        },
        error: function(xhr) {
            //alert('downdate: ' + xhr.responseText);
            $.mobile.hidePageLoadingMsg();
        }
    });
    return false;
};

var sirc_send = function() {
    if($('input#message').hasClass('disabled')) return false;
    var message = $('input#message').val();
    if(channel == '') {
        message = trim(message);
        if(message.length < 1) return false;
        channel = (message.substr(0, 1) == '#' ? '' : '#') + message;
        window.location.hash = encodeURI(channel);
        $('input#message').val('');
        return false;
    }
    if(message.length < 1) return false;
    $.ajax({
        type: 'GET',
        url: '/send/',
        data: 'channel=' + encodeURIComponent(channel) + '&message=' + encodeURIComponent(message),
        dataType: 'xml',
        success: function(xml) {
            $('input#message').removeClass('disabled');
            $('input#message').val('');
            add_process(xml, 'send');
        },
        error: function(xhr) {
            //alert('send: ' + xhr.responseText);
            $('input#message').removeClass('disabled');
        }
    });
    $('input#message').addClass('disabled');
    return false;
};

var sirc_join = function() {
    if(!window.location.hash) return;
    channel = window.location.hash;
    if(channel.length > 2 && channel.charAt(1) == '%') {
        channel = decodeURI(channel);
    }
    $('a#dummy').attr('name', channel.substr(1))
    $('title').html(channel + ' - SIRC');
    $('h1#channel').html(channel);
    $('ul#log').empty();
    $('input#message').attr('placeholder', '');
    last_update = last_downdate = datetime_now();
    sirc_downdate(function() { scroll(SCROLL_END, 1000); });
    setTimeout("sirc_update();", 500);
    return false;
};

var sirc_delete = function(a) {
    $.ajax({
        type: 'GET',
        url: '/delete/',
        data: 'channel=' + encodeURIComponent($(a).attr('channel')),
        success: function() {
            $(a).parent().remove();
        },
        error: function(xhr) {
            //alert('delete: ' + xhr.responseText);
        }
    });
    return false;
};

// Main

$(document).ready(function() {
    $('div#quick_channel a').click(function() { $('div#quick_channel').hide(); });
    $('a#quickening').click(function() { $('div#quick_channel').toggle(); return false; });
    $('a#setting').click(function() { $('div#menu').toggle(); return false; });
    $('a[sirc="delete"]').click(function() { return sirc_delete(this); });
    $('form#send').submit(function() { return sirc_send(); });
    $('input#message').keydown(function (e) { if(e.keyCode == 13) return sirc_send(); });
    $(window).hashchange(function() { if(window.location.hash == '') window.location.reload(); transition_id++; return sirc_join(); });
    sirc_join();
});
