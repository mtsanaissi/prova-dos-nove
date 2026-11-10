(async function () {
  const campo = document.getElementById('busca');
  const status = document.getElementById('busca-status');
  const itens = Array.from(document.querySelectorAll('#lista li[data-nome]'));
  const secoes = Array.from(document.querySelectorAll('#lista section[data-ra]'));
  const normaliza = (texto) => String(texto || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR').trim();

  let indice;
  try {
    const resposta = await fetch('indice.json');
    if (!resposta.ok) throw new Error(String(resposta.status));
    indice = await resposta.json();
  } catch (erro) {
    status.textContent = 'A busca por nome não carregou; a lista abaixo continua completa.';
    campo.disabled = true;
    return;
  }

  const porCodigo = new Map(indice.map((item) => [String(item.co_entidade), item]));
  campo.addEventListener('input', () => {
    const termo = normaliza(campo.value);
    let encontrou = false;
    for (const item of itens) {
      const dados = porCodigo.get(item.dataset.codigo);
      const nome = normaliza(dados ? dados.nome : item.dataset.nome);
      const mostrar = !termo || nome.includes(termo);
      item.hidden = !mostrar;
      if (mostrar) encontrou = true;
    }
    for (const secao of secoes) {
      secao.hidden = !secao.querySelector('li:not([hidden])');
    }
    status.textContent = termo && !encontrou ? 'Nenhuma escola encontrada.' : '';
  });
})();
