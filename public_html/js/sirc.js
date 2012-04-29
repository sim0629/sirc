/* sirc.js */

// Global Variables

var channel = '';
var last_update = '';
var last_downdate = '';

// Utility

var add_process = function(xml, flag) {
	$('log', xml).each(function(i) {
		var datetime = $(this).find('datetime').text();
		var source = $(this).find('source').text();
		var message = $(this).find('message').text();
		append_log(flag, datetime, source, message);
	});
	$('ul#log').listview('refresh');
	if(flag != 'downdate')
		scroll(SCROLL_END, 1000);
};

var append_log = function(flag, datetime, source, message) {
	var element = $('<li><div class="datetime">' + datetime_format(datetime) + '</div><div class="source">&lt;<span class="nick">' + html_encode(source) + '</span>&gt;</div><div class="message">' + html_encode(message) + '</div></li>');
	if(flag == 'downdate') {
		element.prependTo($('ul#log'));
		last_downdate = datetime;
	}else {
		element.appendTo($('ul#log')).attr('flag', flag);
		if(flag != 'send') last_update = datetime;
	}
};

var datetime_format = function(datetime) {
	return datetime.substr(0, 19).replace(' ', '<br />');
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
	return s;
};

var SCROLL_END = -1;
var scroll = function(pos, duration) {
	if($('#scrolling').val() == 'off') return;
	if(pos == SCROLL_END) pos = $('ul#log').height();
	$('body,html,document').animate({scrollTop: pos}, duration);
};

// Ajax Calls

var sirc_update = function() {
	if(channel == '') return false;
	$.ajax({
		type: 'GET',
		url: '/sgm/update/',
		data: 'channel=' + encodeURIComponent(channel) + '&last_update=' + encodeURIComponent(last_update),
		dataType: 'xml',
		success: function(xml) {
			add_process(xml, 'update');
			$('ul#log > li[flag="send"]').remove();
		},
		error: function(xhr) {
			alert('update: ' + xhr.responseText);
		}
	});
	return false;
};

var sirc_downdate = function() {
	if(channel == '') return false;
	$.mobile.showPageLoadingMsg();
	$.ajax({
		type: 'GET',
		url: '/sgm/downdate/',
		data: 'channel=' + encodeURIComponent(channel) + '&last_downdate=' + encodeURIComponent(last_downdate),
		dataType: 'xml',
		success: function(xml) {
			add_process(xml, 'downdate');
			$('<li>more</li>').click(function() { $(this).remove(); return sirc_downdate(); }).prependTo($('ul#log'));
			$.mobile.hidePageLoadingMsg();
		},
		error: function(xhr) {
			alert('downdate: ' + xhr.responseText);
			$.mobile.hidePageLoadingMsg();
		}
	});
	return false;
};

var sirc_send = function() {
	if(channel == '') return false;
	var message = $('input#message').val();
	if(message == '') return false;
	$.ajax({
		type: 'GET',
		url: '/sgm/send/',
		data: 'channel=' + encodeURIComponent(channel) + '&message=' + encodeURIComponent($('input#message').val()),
		dataType: 'xml',
		success: function(xml) {
			add_process(xml, 'send');
			$('input#message').val('');
			$('form#send').removeAttr('disabled');
		},
		error: function(xhr) {
			alert('send: ' + xhr.responseText);
			$('form#send').removeAttr('disabled');
		}
	});
	$('form#send').attr('disabled', 'disabled');
	return false;
};

var sirc_join = function() {
	if(!window.location.hash) return;
	channel = window.location.hash;
	$('a#dummy').attr('name', channel.substr(1))
	$('title').html(channel + ' - SIRC');
	$('h1#channel').html(channel);
	$('ul#log').empty();
	last_update = last_downdate = datetime_now();
	sirc_downdate();
	sirc_update();
	return false;
};

// Main

$(document).ready(function() {
	$('a#update').click(function() { return sirc_update(); });
	$('a#setting').click(function() { $('div#menu').toggle(); return false; });
	$('form#send').submit(function() { return sirc_send(); });
	$('input#message').keydown(function (e) { if(e.keyCode == 13) return sirc_send(); });
	$(window).hashchange(function() { return sirc_join(); });
	sirc_join();
});
