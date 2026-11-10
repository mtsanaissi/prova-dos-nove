(async function () {
  const searchField = document.getElementById('busca');
  const status = document.getElementById('busca-status');
  const items = Array.from(document.querySelectorAll('#lista li[data-nome]'));
  const sections = Array.from(document.querySelectorAll('#lista section[data-ra]'));
  const jumpSelect = document.getElementById('ir-ra');
  const jumpOptions = Array.from(jumpSelect.querySelectorAll('option[value^="#ra-"]'));
  const normalize = (text) => String(text || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR').trim();

  jumpSelect.addEventListener('change', () => {
    const target = jumpSelect.value;
    if (!target) return;
    const section = document.getElementById(target.slice(1));
    if (!section || section.hidden) {
      jumpSelect.value = '';
      return;
    }
    if (location.hash === target) {
      section.scrollIntoView();
    } else {
      location.hash = target;
    }
    jumpSelect.value = '';
  });

  let searchIndex;
  try {
    const response = await fetch('indice.json');
    if (!response.ok) throw new Error(String(response.status));
    searchIndex = await response.json();
  } catch (error) {
    status.textContent = 'A busca por nome não carregou; a lista abaixo continua completa.';
    searchField.disabled = true;
    return;
  }

  const byCode = new Map(searchIndex.map((entry) => [String(entry.co_entidade), entry]));
  searchField.addEventListener('input', () => {
    const term = normalize(searchField.value);
    let found = false;
    for (const item of items) {
      const entry = byCode.get(item.dataset.codigo);
      const name = normalize(entry ? entry.nome : item.dataset.nome);
      const show = !term || name.includes(term);
      item.hidden = !show;
      if (show) found = true;
    }
    for (const section of sections) {
      section.hidden = !section.querySelector('li:not([hidden])');
    }
    for (const option of jumpOptions) {
      const section = document.getElementById(option.value.slice(1));
      const visible = Boolean(section && !section.hidden);
      option.hidden = !visible;
      option.disabled = !visible;
      if (!visible && option.selected) {
        jumpSelect.value = '';
      }
    }
    jumpSelect.disabled = sections.every((section) => section.hidden);
    status.textContent = term && !found ? 'Nenhuma escola encontrada.' : '';
  });
})();
