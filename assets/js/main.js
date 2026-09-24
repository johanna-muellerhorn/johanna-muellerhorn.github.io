/*
	Read Only by HTML5 UP
	html5up.net | @ajlkn
	Free for personal and commercial use under the CCA 3.0 license (html5up.net/license)
*/

(function($) {

	var $window = $(window),
		$body = $('body'),
		$header = $('#header'),
		$titleBar = null,
		$nav = $('#nav'),
		$wrapper = $('#wrapper');

	// Breakpoints.
		breakpoints({
			xlarge:   [ '1281px',  '1680px' ],
			large:    [ '1025px',  '1280px' ],
			medium:   [ '737px',   '1024px' ],
			small:    [ '481px',   '736px'  ],
			xsmall:   [ null,      '480px'  ],
		});

	// Play initial animations on page load.
		$window.on('load', function() {
			window.setTimeout(function() {
				$body.removeClass('is-preload');
			}, 100);
		});

	// Tweaks/fixes.

		// Polyfill: Object fit.
			if (!browser.canUse('object-fit')) {

				$('.image[data-position]').each(function() {

					var $this = $(this),
						$img = $this.children('img');

					// Apply img as background.
						$this
							.css('background-image', 'url("' + $img.attr('src') + '")')
							.css('background-position', $this.data('position'))
							.css('background-size', 'cover')
							.css('background-repeat', 'no-repeat');

					// Hide img.
						$img
							.css('opacity', '0');

				});

			}

	// Header Panel.

		// Nav.
			var $nav_a = $nav.find('a'),
				unlockTimeout = null;

			$nav_a
				.addClass('scrolly')
				.on('click', function() {

					var $this = $(this);

					// External link? Bail.
						if ($this.attr('href').charAt(0) != '#')
							return;

					// Deactivate all links.
						$nav_a.removeClass('active active-locked');

					// Activate link *and* lock it (so Scrollex doesn't try to activate other links as we're scrolling to this one's section).
						$this
							.addClass('active')
							.addClass('active-locked');

					// Release the lock once the scroll animation (1000ms) has finished, in case the
					// target section never reaches the middle of the viewport (e.g. Contact at the page bottom).
						window.clearTimeout(unlockTimeout);
						unlockTimeout = window.setTimeout(function() {
							$this.removeClass('active-locked');
						}, 1100);

					// Close the slide-out panel (small screens). Scrolly does the scrolling; the panel's own
					// hideOnClick redirect is disabled because its delayed jump to the anchor made the
					// highlighted nav item flicker to the previous section mid-scroll.
						$body.removeClass('header-visible');

				})
				.each(function() {

					var	$this = $(this),
						id = $this.attr('href'),
						$section = $(id);

					// No section for this link? Bail.
						if ($section.length < 1)
							return;

					// Scrollex.
						$section.scrollex({
							mode: 'middle',
							top: '5vh',
							bottom: '5vh',
							initialize: function() {

								// Deactivate section.
									$section.addClass('inactive');

							},
							enter: function() {

								// Activate section.
									$section.removeClass('inactive');

								// No locked links? Deactivate all links and activate this section's one.
									if ($nav_a.filter('.active-locked').length == 0) {

										$nav_a.removeClass('active');
										$this.addClass('active');

									}

								// Otherwise, if this section's link is the one that's locked, unlock it.
									else if ($this.hasClass('active-locked'))
										$this.removeClass('active-locked');

							}
						});

				});

		// Title Bar.
			$titleBar = $(
				'<div id="titleBar">' +
					'<a href="#header" class="toggle"></a>' +
					'<span class="title">' + $('#logo').html() + '</span>' +
				'</div>'
			)
				.appendTo($body);

		// Panel.
			$header
				.panel({
					delay: 500,
					hideOnClick: false,
					hideOnSwipe: true,
					resetScroll: true,
					resetForms: true,
					side: 'right',
					target: $body,
					visibleClass: 'header-visible'
				});

	// Scrolly.
		$('.scrolly').scrolly({
			speed: 1000,
			offset: function() {

				if (breakpoints.active('<=medium'))
					return $titleBar.height();

				return 0;

			}
		});

	// Research Carousel.
		var $carouselContainer = $('.carousel-container');
		var $articles = $carouselContainer.find('article');
		var totalSlides = $articles.length;
		var currentSlide = 0;

		// Distance between slides (article width + CSS gap), measured on demand so it stays correct after resizing.
		function slideOffset(slideIndex) {
			if (!totalSlides)
				return 0;

			return $articles[slideIndex].offsetLeft - $articles[0].offsetLeft;
		}

		function goToSlide(slideIndex) {
			$carouselContainer.stop().animate({scrollLeft: slideOffset(slideIndex)}, 1000, 'linear');
			currentSlide = slideIndex;
		}

		// Keep the current slide aligned when the window is resized.
		$window.on('resize', function() {
			$carouselContainer.stop().scrollLeft(slideOffset(currentSlide));
		});

		$('.carousel-prev').on('click', function() {
			var nextSlide = (currentSlide - 1 + totalSlides) % totalSlides;
			goToSlide(nextSlide);
		});

		$('.carousel-next').on('click', function() {
			var nextSlide = (currentSlide + 1) % totalSlides;
			goToSlide(nextSlide);
		});

		// Auto-advance every 10 seconds
		var autoAdvance = setInterval(function() {
			$('.carousel-next').trigger('click');
		}, 10000);

		// Pause and restart on user interaction
		$carouselContainer.on('scroll', function() {
			clearInterval(autoAdvance);
			autoAdvance = setInterval(function() {
				$('.carousel-next').trigger('click');
			}, 10000);
		});

		$('.carousel-prev, .carousel-next').on('click', function() {
			clearInterval(autoAdvance);
			autoAdvance = setInterval(function() {
				$('.carousel-next').trigger('click');
			}, 10000);
		});

	// Reveal on first view (intro section): .reveal elements slide/fade in once when they
	// first enter the viewport. Without IntersectionObserver, show everything immediately.
		var revealElements = document.querySelectorAll('.reveal');

		// Tells the fail-safe timer in <head> that the reveal logic is running.
		window.revealReady = true;

		if ('IntersectionObserver' in window) {

			var revealObserver = new IntersectionObserver(function(entries) {
				entries.forEach(function(entry) {

					if (!entry.isIntersecting)
						return;

					entry.target.classList.add('is-visible');
					revealObserver.unobserve(entry.target);

				});
			}, { threshold: 0.15 });

			revealElements.forEach(function(el) {
				revealObserver.observe(el);
			});

		}
		else
			$(revealElements).addClass('is-visible');

})(jQuery);