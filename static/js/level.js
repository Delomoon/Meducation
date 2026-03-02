const gridEl = document.getElementById('grid');
const codeEl = document.getElementById('code');
const resultEl = document.getElementById('result');
const runBtn = document.getElementById('run-btn');
const startedAt = Date.now();

if (gridEl) {
  const width = Number(gridEl.dataset.width);
  const height = Number(gridEl.dataset.height);
  const start = JSON.parse(gridEl.dataset.start);
  const finish = JSON.parse(gridEl.dataset.finish);
  const obstacles = JSON.parse(gridEl.dataset.obstacles);

  gridEl.style.gridTemplateColumns = `repeat(${width}, 64px)`;

  function draw(playerPos) {
    gridEl.innerHTML = '';
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const cell = document.createElement('div');
        cell.className = 'cell';

        if (x === finish[0] && y === finish[1]) {
          cell.classList.add('finish');
          cell.textContent = '🏁';
        }

        if (obstacles.some((o) => o[0] === x && o[1] === y)) {
          cell.classList.add('obstacle');
          cell.textContent = '🧱';
        }

        if (x === playerPos[0] && y === playerPos[1]) {
          cell.textContent = '🧑‍💻';
        }

        gridEl.appendChild(cell);
      }
    }
  }

  draw(start);

  runBtn?.addEventListener('click', async () => {
    resultEl.textContent = 'Выполняем...';
    const elapsedMs = Date.now() - startedAt;

    const response = await fetch(`/api/level/${window.LEVEL_ID}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: codeEl.value, elapsed_ms: elapsedMs }),
    });

    const data = await response.json();
    if (!response.ok) {
      resultEl.textContent = data.error || 'Ошибка выполнения';
      return;
    }

    draw(data.final_pos);

    const details = [];
    details.push(data.message);
    if (data.errors.length) {
      details.push(`Ошибки: ${data.errors.join('; ')}`);
    }
    details.push(`Звёзды за попытку: ${data.stars.total_attempt}/3`);
    resultEl.textContent = details.join(' | ');
  });
}
