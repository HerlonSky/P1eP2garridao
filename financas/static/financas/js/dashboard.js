// Gráficos do dashboard (Chart.js).
// O Django continua sendo o dono dos dados: a view calcula as métricas e o
// template as escreve na página com o filtro json_script. Aqui só lemos esse
// JSON e desenhamos.

(function () {
    if (typeof Chart === 'undefined') return; // CDN indisponível: as tabelas continuam na página

    // Cores categóricas em ordem fixa (paleta validada para daltonismo).
    // Receitas e despesas usam sempre os slots 1 e 2; o ranking (série única) usa uma cor só.
    const COR = {
        receitas: '#257de0',
        despesas: '#f47230',
        ranking: '#6a4ce2',
        outras: '#9aa0a6',
    };
    const CORES_CONTAS = ['#257de0', '#f47230', '#00b894', '#f2a600', '#ee7fac'];
    const TEXTO = '#3f3457';
    const GRADE = 'rgba(63, 52, 87, 0.08)';

    const reais = (v) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    Chart.defaults.font.family = "'Quicksand', 'Segoe UI', sans-serif";
    Chart.defaults.color = TEXTO;
    Chart.defaults.plugins.tooltip.callbacks.label = (ctx) => {
        const valor = ctx.parsed.y ?? ctx.parsed.x ?? ctx.parsed;
        const nome = ctx.dataset.label || ctx.label;
        return `${nome}: ${reais(valor)}`;
    };

    function ler(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : null;
    }

    const eixoValor = {
        beginAtZero: true,
        grid: { color: GRADE },
        border: { display: false },
        ticks: { callback: (v) => reais(v) },
    };
    const eixoCategoria = { grid: { display: false }, border: { display: false } };

    const graficos = ler('dados-graficos');
    if (!graficos) return;

    // Série no tempo: receitas × despesas por mês (barras agrupadas, um só eixo).
    const canvasSerie = document.getElementById('grafico-serie');
    if (canvasSerie && graficos.serie.length) {
        new Chart(canvasSerie, {
            type: 'bar',
            data: {
                labels: graficos.serie.map((d) => d.mes),
                datasets: [
                    { label: 'Receitas', data: graficos.serie.map((d) => d.receitas), backgroundColor: COR.receitas },
                    { label: 'Despesas', data: graficos.serie.map((d) => d.despesas), backgroundColor: COR.despesas },
                ],
            },
            options: {
                maintainAspectRatio: false,
                datasets: { bar: { borderRadius: 4, maxBarThickness: 28, categoryPercentage: 0.7, barPercentage: 0.9 } },
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { position: 'top', align: 'end', labels: { boxWidth: 12, boxHeight: 12 } } },
                scales: { x: eixoCategoria, y: eixoValor },
            },
        });
    }

    // Ranking: categorias com mais gastos (barras horizontais, série única: sem legenda).
    const canvasRanking = document.getElementById('grafico-ranking');
    if (canvasRanking && graficos.ranking.length) {
        new Chart(canvasRanking, {
            type: 'bar',
            data: {
                labels: graficos.ranking.map((d) => d.rotulo),
                datasets: [{ label: 'Gasto', data: graficos.ranking.map((d) => d.total), backgroundColor: COR.ranking }],
            },
            options: {
                indexAxis: 'y',
                maintainAspectRatio: false,
                datasets: { bar: { borderRadius: 4, maxBarThickness: 22 } },
                plugins: { legend: { display: false } },
                scales: { x: eixoValor, y: eixoCategoria },
            },
        });
    }

    // Distribuição: despesas por conta (rosca com poucas fatias; o resto vira "Outras").
    const canvasDistribuicao = document.getElementById('grafico-distribuicao');
    if (canvasDistribuicao && graficos.distribuicao.length) {
        new Chart(canvasDistribuicao, {
            type: 'doughnut',
            data: {
                labels: graficos.distribuicao.map((d) => d.rotulo),
                datasets: [{
                    data: graficos.distribuicao.map((d) => d.total),
                    backgroundColor: graficos.distribuicao.map((d) => (d.cor === null ? COR.outras : CORES_CONTAS[d.cor])),
                    borderColor: '#ffffff',
                    borderWidth: 2, // separa as fatias
                }],
            },
            options: {
                maintainAspectRatio: false,
                cutout: '62%',
                plugins: { legend: { position: 'right', labels: { boxWidth: 12, boxHeight: 12 } } },
            },
        });
    }
})();
