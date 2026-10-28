/* OSStore — melhorias progressivas. O site funciona sem este arquivo. */
(function () {
  "use strict";

  /* Menu no celular */
  var toggle = document.querySelector(".menu-toggle");
  var nav = document.getElementById("nav-principal");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var aberto = nav.classList.toggle("aberto");
      toggle.setAttribute("aria-expanded", aberto ? "true" : "false");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("aberto")) {
        nav.classList.remove("aberto");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  /* Galeria do produto: miniatura troca a imagem principal */
  var principal = document.getElementById("galeria-principal-img");
  var miniaturas = document.querySelectorAll("[data-galeria-thumb]");
  miniaturas.forEach(function (link) {
    link.addEventListener("click", function (e) {
      if (!principal) { return; }
      e.preventDefault();
      principal.src = link.getAttribute("href");
      principal.alt = link.getAttribute("data-alt") || principal.alt;
      miniaturas.forEach(function (l) { l.classList.remove("ativa"); l.removeAttribute("aria-current"); });
      link.classList.add("ativa");
      link.setAttribute("aria-current", "true");
    });
  });

  /* Quantidade: botões +/- respeitam o estoque da opção escolhida */
  var form = document.getElementById("form-compra");
  if (form) {
    var qtd = form.querySelector("input[name=quantidade]");
    var aviso = document.getElementById("aviso-estoque");

    function limite() {
      var marcado = form.querySelector("input[name=variante]:checked");
      var max = marcado ? parseInt(marcado.getAttribute("data-estoque"), 10) : parseInt(qtd.getAttribute("data-estoque-base"), 10);
      return isNaN(max) || max < 1 ? 1 : Math.min(max, 99);
    }
    function ajustar() {
      var max = limite();
      qtd.max = max;
      if (parseInt(qtd.value, 10) > max) { qtd.value = max; }
      if (parseInt(qtd.value, 10) < 1 || isNaN(parseInt(qtd.value, 10))) { qtd.value = 1; }
      if (aviso) {
        var marcado = form.querySelector("input[name=variante]:checked");
        aviso.textContent = marcado ? (max <= 5 ? "Restam " + max + " unidade(s) desta opção." : "") : "";
      }
    }
    form.querySelectorAll("[data-qtd]").forEach(function (b) {
      b.addEventListener("click", function () {
        var v = parseInt(qtd.value, 10) || 1;
        v += b.getAttribute("data-qtd") === "mais" ? 1 : -1;
        qtd.value = v;
        ajustar();
      });
    });
    form.querySelectorAll("input[name=variante]").forEach(function (r) { r.addEventListener("change", ajustar); });
    qtd.addEventListener("change", ajustar);
    ajustar();
  }
})();
