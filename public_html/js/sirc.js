/* 졸려 by sgm */

datetime_format = function(datetime) {
	return datetime.substr(0, 19).replace(' ', '<br />');
};

html_encode = function(s) {
	var e = document.createElement('div');
	e.innerText = e.textContent = s;
	s = e.innerHTML;
	delete e;
	return s;
};

scroll2end = function() {
	var log = document.getElementById('log');
	log.scrollTop = log.scrollHeight;
};

append_log = function(datetime, source, message) {
	$('ul').append('<li class="ui-li-static"><div class="datetime">' + datetime_format(datetime) + '</div><div class="source">&lt;<span class="nick">' + html_encode(source) + '</span>&gt;</div><div class="message">' + html_encode(message) + '</div></li>');
	scroll2end();
};

add_process = function(xml) {
	$('log', xml).each(function() {
		var datetime = $(this).find('datetime').text();
		var source = $(this).find('source').text();
		var message = $(this).find('message').text();
		append_log(datetime, source, message);
	});
};

sirc_update = function() {
	$.ajax({
		type: 'GET',
		url: '/sgm/update/',
		dataType: 'xml',
		success: function(xml) {
			add_process(xml);
			//setTimeout(sirc_update, 1000);
		},
		error: function() {
			//setTimeout(sirc_update, 1000);
		}
	});
};

/*
datetime_format = function(d) {
	return d.getFullYear() + '-' + (d.getMonth() < 9 ? '0' : '') + (d.getMonth() + 1) + '-' + (d.getDate() < 10 ? '0' : '') + d.getDate() + ' ' + (d.getHours() < 10 ? '0' : '') + d.getHours() + ':' + (d.getMinutes() < 10 ? '0' : '') + d.getMinutes() + ':' + (d.getSeconds() < 10 ? '0' : '') + d.getSeconds();
};
*/
$(document).ready(function() {
	$('#log').height($('body').height() - 80);
	touchScroll('log');
	$('.datetime').each(function() {
		$(this).html(datetime_format($(this).html()));
	});
	$('li').each(function() {
		$(this).attr('class', 'ui-li-static');
	});
	scroll2end();
	//sirc_update();
	$('#form').submit(function() {
		$(this).ajaxSubmit({
			success: function(xml) {
				add_process(xml);
				$('#input').val('');
			}
		});
		return false;
	});
});
