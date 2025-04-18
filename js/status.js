const apiUrl = 'https://your-domain.com/api/status';

// DOM 요소 생성 헬퍼 함수
function createElement(tag, className = '', textContent = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element;
}

// 검색 입력창 생성
function searchBox() {
    const searchContainer = createElement('div', 'search-container');
    const searchInput = createElement('input', 'search-input');
    searchInput.type = 'text';
    searchInput.placeholder = '검색어를 입력하세요...';
    searchContainer.appendChild(searchInput);
    return { searchContainer, searchInput };
}

// 로딩 상태 표시
function loadingElement() {
    const container = createElement('div', 'loading-container');
    const spinner = createElement('div', 'loading-spinner');
    const text = createElement('div', '', '불러오는 중...');
    container.appendChild(spinner);
    container.appendChild(text);
    return container;
}

// 에러 메시지
function errorElement(message) {
    return createElement('div', 'error-message', message);
}

// 스케줄러 테이블 생성
function schedulerTable(env, ruleList) {
    const table = createElement('table');
    table.dataset.env = env; // 환경 정보를 데이터 속성으로 저장
    
    // 테이블 헤더 생성
    const thead = createElement('thead');
    const headerRow1 = createElement('tr');
    const envHeader = createElement('th');
    envHeader.colSpan = 2; // 환경 헤더 컬럼 2개 병합
    envHeader.textContent = env;
    headerRow1.appendChild(envHeader);
    
    const headerRow2 = createElement('tr');
    headerRow2.appendChild(createElement('th', '', 'Rule'));
    headerRow2.appendChild(createElement('th', '', 'Schedule'));
    
    thead.appendChild(headerRow1);
    thead.appendChild(headerRow2);
    table.appendChild(thead);
    
    // 테이블 본문 생성
    const tbody = createElement('tbody');
    
    if (Array.isArray(ruleList)) {
        ruleList.forEach(rule => {
            const row = createElement('tr');
            row.dataset.ruleName = rule.name; // 규칙 이름을 데이터 속성으로 저장
            row.dataset.schedule = rule.schedule; // 스케줄을 데이터 속성으로 저장
            row.appendChild(createElement('td', '', rule.name));
            row.appendChild(createElement('td', '', rule.schedule));
            tbody.appendChild(row);
        });
    } else {
        const row = createElement('tr');
        const errorCell = createElement('td', 'error-message');
        errorCell.colSpan = 2; // 오류 메시지 컬럼 2개 병합
        errorCell.textContent = ruleList;
        row.appendChild(errorCell);
        tbody.appendChild(row);
    }
    
    table.appendChild(tbody);
    return table;
}

// 테이블 필터링 함수
function filterTables(searchText) {
    const tables = document.querySelectorAll('table'); // 모든 테이블 선택
    const searchLower = searchText.toLowerCase(); // toLowerCase 함수로 소문자 변환

    // 테이블 조회
    tables.forEach(table => {
        let hasVisibleRows = false; // 표시된 행 여부 확인 변수
        const rows = table.querySelectorAll('tbody tr'); // tbody 내의 모든 tr 선택
        
        // 각 행 조희
        rows.forEach(row => {
            const env = table.dataset.env?.toLowerCase() || ''; // ||'' 으로 에러 방지
            const ruleName = row.dataset.ruleName?.toLowerCase() || '';
            const schedule = row.dataset.schedule?.toLowerCase() || '';
            
            // 환경명, 규칙명, 스케줄 중 하나라도 검색어를 포함하면 표시
            const isVisible = env.includes(searchLower) || ruleName.includes(searchLower) || schedule.includes(searchLower);
            
            row.style.display = isVisible ? '' : 'none'; // 검색어 포함 여부에 따라 표시 여부 설정
            if (isVisible) hasVisibleRows = true; // 표시된 행이 있으면 true로 설정
        });
        
        // 표시할 행이 없는 테이블은 숨김
        table.style.display = hasVisibleRows ? '' : 'none';
        // 테이블 다음의 br 태그도 같이 숨김/표시
        const nextBr = table.nextElementSibling; // 테이블 다음의 요소 선택 
        if (nextBr && nextBr.tagName === 'BR') { // br 태그인 경우
            nextBr.style.display = hasVisibleRows ? '' : 'none'; // 표시 여부 설정
        }
    });
}

// API 요청 함수 (재시도 로직 포함)
async function fetchRetry(retryCount = 0) {
    const maxRetries = 2; // 최대 재시도 횟수
    const retryDelay = 1000; // 재시도 대기 시간 (ms)

    try {
        const response = await fetch(apiUrl, {
            method: 'GET',
            credentials: 'include'
        });

        // API Gateway 504 경우 재시도
        if (response.status === 504 && retryCount < maxRetries) {
            console.log(`재시도 중... (${retryCount + 1}/${maxRetries})`);
            await new Promise(resolve => setTimeout(resolve, retryDelay));
            return fetchRetry(retryCount + 1);
        }

        return response;
    } catch (error) {
        if (retryCount < maxRetries) {
            console.log(`네트워크 오류로 재시도 중... (${retryCount + 1}/${maxRetries})`);
            await new Promise(resolve => setTimeout(resolve, retryDelay));
            return fetchRetry(retryCount + 1);
        }
        throw error;
    }
}

async function statusbox() {
    const container = document.getElementById('status-container');
    
    // 기존 내용 제거
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    
    // 로딩 상태 표시
    container.appendChild(loadingElement());

    try {
        const response = await fetchRetry();

        if (!response.ok) {
            container.replaceChildren(
                errorElement(`상태 오류 발생: ${response.status}`)
            );
            return;
        }

        const data = await response.json();
        const rules = data.rules;

        container.replaceChildren(); // 기존 내용 제거
        
        if (!rules || Object.keys(rules).length === 0) {
            container.appendChild(
                errorElement('가져올 스케줄러가 없습니다.')
            );
            return;
        }

        // 검색창 추가
        const { searchContainer, searchInput } = searchBox();
        container.appendChild(searchContainer);
        
        // 실시간 검색 이벤트 리스너
        searchInput.addEventListener('input', (e) => {
            filterTables(e.target.value);
        });

        // 각 환경별 테이블 생성 및 추가
        for (const [env, ruleList] of Object.entries(rules)) {
            const table = schedulerTable(env, ruleList);
            container.appendChild(table);
            container.appendChild(createElement('br'));
        }

    } catch (error) {
        container.replaceChildren(
            errorElement(`오류 발생: ${error.message}`)
        );
    }
}