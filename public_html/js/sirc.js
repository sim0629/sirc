/* 졸려 by sgm */

var auto_polling = function() {
	return $('#flip-polling').val();
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

var append_log = function(datetime, source, message) {
	$('ul').append('<li><div class="datetime">' + datetime_format(datetime) + '</div><div class="source">&lt;<span class="nick">' + html_encode(source) + '</span>&gt;</div><div class="message">' + html_encode(message) + '</div></li>');
};

var add_process = function(xml) {
	$('log', xml).each(function(i) {
		var datetime = $(this).find('datetime').text();
		var source = $(this).find('source').text();
		var message = $(this).find('message').text();
		append_log(datetime, source, message);
	});
	scroll_end();
	$('#log > ul').listview('refresh');
};

var scroll_end = function() {
	//alert($('#log').height());
	$('body,html,document').animate({scrollTop: $('#log').height()}, 1000);
	//$('#wrapper').scrollTop($('#wrapper').height());
	//window.scrollTop = window.scrollHeight;
//('').attr('scrollTop', $('body').attr('scrollHeight'));
}

var sirc_update = function() {
	$.ajax({
		type: 'GET',
		url: '/sgm/update/',
		dataType: 'xml',
		success: function(xml) {
			add_process(xml);
			$('#button').removeAttr('disabled');
		},
		error: function() {
			$('#button').removeAttr('disabled');
		}
	});
	$('#button').attr('disabled', 'disabled');
	return false;
};

var sirc_setting = function() {
	$('#setting').toggle();
};

$(document).ready(function() {
	$('.datetime').each(function() {
		$(this).html(datetime_format($(this).html()));
	});
	scroll_end();
	$('#form').submit(function() {
		$(this).ajaxSubmit({
			success: function(xml) {
				add_process(xml);
				$('#input').val('');
				$('#input').removeAttr('disabled');
				$('#input').removeClass('disabled');
			},
			error: function() {
				$('#input').removeAttr('disabled');
				$('#input').removeClass('disabled');
			}
		});
		$('#input').attr('disabled', 'disabled');
		$('#input').addClass('disabled');
		return false;
	});
});
