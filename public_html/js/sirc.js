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

append_log = function(datetime, source, message) {
	$('ul').append('<li><div class="datetime">' + datetime_format(datetime) + '</div><div class="source">&lt;<span class="nick">' + html_encode(source) + '</span>&gt;</div><div class="message">' + html_encode(message) + '</div></li>');
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

$(document).ready(function() {
	$('.datetime').each(function() {
		$(this).html(datetime_format($(this).html()));
	});
	//sirc_update();
	$('#form').submit(function() {
		$(this).ajaxSubmit({
			success: function(xml) {
				$('#input').val('');
			}
		});
		return false;
	});
});
