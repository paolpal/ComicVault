$(document).ready(function(){
	$('.carousel-inner').slick({
		dots: true,
		autoplay: false,
		arrows: false,
		rtl: true,
		infinite: false,
		adaptiveHeight: false,
	});

	let zoom = 1;
    let isZoomed = false;

    $('.carousel-inner').on('click', '.slick-active img', function(event) {
        const fumetto = $(this);
        if (!isZoomed) {
            zoom = 2;
            isZoomed = true;
        } else {
            zoom = 1;
            isZoomed = false;
        }
        updateTransform(event, fumetto);
    });

    $('.carousel-inner').on('mousemove', '.slick-active img', function(event) {
        if (isZoomed) {
            const fumetto = $(this);
            updateTransform(event, fumetto);
        }
    });

    function updateTransform(event, fumetto) {
        const rect = fumetto[0].getBoundingClientRect();
        const offsetX = event.clientX - rect.left;
        const offsetY = event.clientY - rect.top;
        const originX = (offsetX / rect.width) * 100;
        const originY = (offsetY / rect.height) * 100;

        fumetto.css('transform-origin', `${originX}% ${originY}%`);
        fumetto.css('transform', `scale(${zoom})`);
    }
});