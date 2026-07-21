/* Scroll Progress */

window.addEventListener("scroll", () => {

    let scroll =
        document.documentElement.scrollTop;

    let height =
        document.documentElement.scrollHeight -
        document.documentElement.clientHeight;

    let progress =
        (scroll / height) * 100;

    document.getElementById("progress-bar").style.width =
        progress + "%";

});