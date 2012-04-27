/* sirc.js */

// Global Variables

var channel = '';
var last_update = '';

// Utility

var add_process = function(xml) {
	$('log', xml).each(function(i) {
		var flag = $(this).find('flag').text();
		var datetime = $(this).find('datetime').text();
		var source = $(this).find('source').text();
		var message = $(this).find('message').text();
		append_log(flag, datetime, source, message);
	});
	scroll(SCROLL_END);
	$('ul#log').listview('refresh');
};

var append_log = function(flag, datetime, source, message) {
	$('<li><div class="datetime">' + datetime_format(datetime) + '</div><div class="source">&lt;<span class="nick">' + html_encode(source) + '</span>&gt;</div><div class="message">' + html_encode(message) + '</div></li>').appendTo($('ul#log')).attr('flag', flag);
	if(flag != 'send') last_update = datetime;
};

var datetime_format = function(datetime) {
	return datetime.substr(0, 19).replace(' ', '<br />');
};

var html_encode = function(s) {
	var e = document.createElement('div');
	e.innerText = e.textContent = s;
	s = e.innerHTML;
	delete e;
	return s;
};

var SCROLL_END = -1;
var scroll = function(pos) {
	if($('#scrolling').val() == 'off') return;
	if(pos == SCROLL_END) pos = $('ul#log').height();
	$('body,html,document').animate({scrollTop: pos}, 1000);
};

// Ajax Calls

var sirc_update = function() {
	$.mobile.showPageLoadingMsg();
	$.ajax({
		type: 'GET',
		url: '/sgm/update/',
		data: 'channel=' + encodeURIComponent(channel) + '&last_update=' + encodeURIComponent(last_update),
		dataType: 'xml',
		success: function(xml) {
			add_process(xml);
			$('a#update').removeAttr('disabled');
			$('ul#log > li[flag="send"]').remove();
			$.mobile.hidePageLoadingMsg();
		},
		error: function(xhr) {
			alert(xhr.responseText);
			$('a#update').removeAttr('disabled');
			$.mobile.hidePageLoadingMsg();
		}
	});
	$('a#update').attr('disabled', 'disabled');
	return false;
};

var sirc_send = function() {
	var message = $('input#message').val();
	if(message == '') return false;
	$.ajax({
		type: 'GET',
		url: '/sgm/send/',
		data: 'channel=' + encodeURIComponent(channel) + '&message=' + encodeURIComponent($('input#message').val()),
		dataType: 'xml',
		success: function(xml) {
			add_process(xml);
			$('input#message').val('');
			$('form#send').removeAttr('disabled');
		},
		error: function(xhr) {
			alert(xhr.responseText);
			$('form#send').removeAttr('disabled');
		}
	});
	$('form#send').attr('disabled', 'disabled');
	return false;
};

var sirc_join = function() {
	if(!window.location.hash) return;
	channel = window.location.hash;
	$('title').html(channel + ' - SIRC');
	$('h1#channel').html(channel);
	$('ul#log').empty();
	last_update = '';
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
