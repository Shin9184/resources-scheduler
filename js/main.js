// Done 버튼 업데이트 함수: 텍스트박스가 있을 때만 Done 버튼을 표시
function updateDoneButtonForContainer(containerId) {
    const container = document.getElementById(containerId);
    // 컨테이너 내의 모든 Done 버튼을 찾아서 제거
    const existingDoneButtons = container.querySelectorAll('#done-button');
    existingDoneButtons.forEach(button => button.remove());

    const textboxCount = container.getElementsByClassName('textbox-wrapper').length;

    // 텍스트 박스가 하나 이상 있을 때만 Done 버튼 생성
    if (textboxCount > 0) {
        const doneButton = document.createElement('button');
        doneButton.id = 'done-button';
        doneButton.innerHTML = 'Done';
        doneButton.onclick = () => handleDone(containerId);
        container.appendChild(doneButton);
        doneButton.style.display = 'block';
    }
}

// 스케줄러 중지 대상 추가 함수
function addStopTextbox() {
    var container = document.getElementById('stop-textbox-container');
    var wrapper = document.createElement('div');
    wrapper.className = 'textbox-wrapper';

    // 최대 10개까지만 추가 가능하도록 제한
    var currentCount = container.getElementsByClassName('textbox-wrapper').length;
    if (currentCount >= 10) {
        alert('스케줄러 대상은 최대 10개까지만 추가할 수 있습니다. 사용하지 않는 대상은 Delete 버튼을 눌러 삭제해주세요.');
        return;
    }

    // 환경 선택 드롭다운 
    var envSelect = document.createElement('select');
    envSelect.className = 'env-select';
    var environments = ['aws1', 'aws2'];
    environments.forEach(env => {
        var option = document.createElement('option');
        option.value = env;
        option.text = env;
        envSelect.appendChild(option);
    });

    // 태그 입력 텍스트박스 
    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'textbox';
    input.placeholder = 'Scheduler Tag 입력 예: at-biz ...';

    // 시간 입력 텍스트박스 
    var timeInput = document.createElement('input');
    timeInput.type = 'text';
    timeInput.className = 'time-textbox';
    timeInput.placeholder = '시간 입력 예: 13(UTC) -> 22(KST) ';

    // 삭제 버튼 
    var deleteButton = document.createElement('button');
    deleteButton.className = 'delete-button';
    deleteButton.innerHTML = 'Delete';
    deleteButton.onclick = function() {
        container.removeChild(wrapper);
        updateDoneButtonForContainer('stop-textbox-container');
    };

    // 생성된 요소들을 래퍼에 추가
    wrapper.appendChild(envSelect);
    wrapper.appendChild(input);
    wrapper.appendChild(timeInput);
    wrapper.appendChild(deleteButton);
    container.appendChild(wrapper);
    
    updateDoneButtonForContainer('stop-textbox-container');
}

// 스케줄러 시작 대상 추가 함수 (중지와 유사하나 시간 입력 없음)
function addStartTextbox() {
    var container = document.getElementById('start-textbox-container');
    var wrapper = document.createElement('div');
    wrapper.className = 'textbox-wrapper';

    var currentCount = container.getElementsByClassName('textbox-wrapper').length;
    if (currentCount >= 10) {
        alert('스케줄러 대상은 최대 10개까지만 추가할 수 있습니다. 사용하지 않는 대상은 Delete 버튼을 눌러 삭제해주세요.');
        return;
    }

    // 환경 선택 드롭다운
    var envSelect = document.createElement('select');
    envSelect.className = 'env-select';
    var environments = ['aws1', 'aws2'];
    environments.forEach(env => {
        var option = document.createElement('option');
        option.value = env;
        option.text = env;
        envSelect.appendChild(option);
    });

    // 태그 입력 텍스트박스
    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'textbox';
    input.placeholder = 'Scheduler Tag 입력 예: at-biz ...';

    // 삭제 버튼
    var deleteButton = document.createElement('button');
    deleteButton.className = 'delete-button';
    deleteButton.innerHTML = 'Delete';
    deleteButton.onclick = function() {
        container.removeChild(wrapper);
        updateDoneButtonForContainer('start-textbox-container');
    };

    wrapper.appendChild(envSelect);
    wrapper.appendChild(input);
    wrapper.appendChild(deleteButton);
    container.appendChild(wrapper);
    
    updateDoneButtonForContainer('start-textbox-container');
}

// Done 버튼 클릭 시 실행되는 메인 처리 함수
async function handleDone(containerId) {
    try {
        // auth.js의 checkAuthAndRedirect 함수를 먼저 호출하여 인증 상태 확인
        await checkAuthAndRedirect();

        // 로딩 오버레이 생성 및 표시 (처리 중임을 시각적으로 표시)
        let loadingOverlay = document.querySelector('.loading-overlay');
        if (!loadingOverlay) {
            loadingOverlay = document.createElement('div');
            loadingOverlay.className = 'loading-overlay';
            const loadingImg = document.createElement('img');
            loadingImg.src = '../images/runcat.gif';
            loadingImg.alt = '로딩 중...';
            loadingOverlay.appendChild(loadingImg);
            
            // 진행률 표시 요소 추가 (처리 진행상태를 퍼센트로 표시)
            const progressText = document.createElement('div');
            progressText.id = 'progress-text';
            progressText.style.position = 'absolute';
            progressText.style.left = '50%';
            progressText.style.transform = 'translateX(-50%)';
            progressText.style.color = 'white';
            progressText.style.display = 'block';

            // 이미지가 로드된 후 진행률 텍스트 위치 설정
            loadingImg.onload = () => {
                progressText.style.top = `${loadingImg.offsetTop + loadingImg.height + 10}px`;
            };

            loadingOverlay.appendChild(progressText);
            document.body.appendChild(loadingOverlay);
        }
        loadingOverlay.classList.add('active');

        // 입력된 데이터 수집
        const container = document.getElementById(containerId); //containerId로 전달된 ID를 가진 DOM 요소(container)를 찾고 그 안에 있는 .env-select, .textbox, .time-textbox 클래스를 가진 입력 필드들을 가져옴   
        const envSelects = container.getElementsByClassName('env-select'); 
        const textboxes = container.getElementsByClassName('textbox');  
        const timeboxes = container.getElementsByClassName('time-textbox');

        // 성공적으로 처리된 태그를 추적하기 위한 Set 이미 처리된 태그는 다시 포함되지 않도록
        const successfulTags = new Set();

        // 입력값 유효성 검사 및 데이터 구조화
        const values = Array.from(textboxes).map((textbox, index) => ({
            env: envSelects[index]?.value.trim(),
            tag: textbox.value.trim(),
            time: containerId === 'stop-textbox-container' ? timeboxes[index]?.value.trim() : null,
            action: containerId === 'stop-textbox-container' ? 'stop' : 'start'
        })).filter(item => item.env && item.tag && (containerId === 'stop-textbox-container' ? item.time : true) && !successfulTags.has(item.tag));

        // 입력값 검증
        if (values.length === 0) {
            loadingOverlay.classList.remove('active');
            alert(containerId === 'stop-textbox-container' ? '태그와 시간을 입력해주세요.' : '태그를 입력해주세요.');
            return;
        }

        // 태그 형식 검증 (영문자, 숫자, 하이픈만 허용)
        const tagRegex = /^[a-zA-Z0-9-]+$/;
        for (const value of values) {
            if (!tagRegex.test(value.tag)) {
                loadingOverlay.classList.remove('active');
                alert('태그는 영문자, 숫자, 하이픈(-)만 사용할 수 있습니다.');
                return;
            }
        }

        // 시간 형식 검증 (0-23 사이의 숫자)
        if (containerId === 'stop-textbox-container') {
            for (const value of values) {
                const time = parseInt(value.time);
                if (isNaN(time) || time < 0 || time > 23) {
                    loadingOverlay.classList.remove('active');
                    alert('시간은 0-23 사이의 숫자여야 합니다.');
                    return;
                }
            }
        }

        console.log('입력된 값들:', values);

        // API 엔드포인트 설정
        const apiUrl = containerId === 'stop-textbox-container' 
            ? 'https://your-domain.com/api/stop'
            : 'https://your-domain.com/api/start';

        const results = [];
        const errors = [];
        let processedCount = 0;
        const totalCount = values.length;

        // 재시도 로직을 포함한 API 요청 함수
        async function makeRequest(value, retryCount = 0) {
            const maxRetries = 2; // 최대 재시도 횟수
            const retryDelay = 1000; // 재시도 대기 시간 (ms)

            try {
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify([value])
                });

                // 인증 오류 체크
                if (response.status === 401) {
                    throw new Error('AUTH_ERROR');
                }

                // API Gateway 타임아웃 시 재시도
                // Promise와 setTimeout을 사용하여 비동기적인 재시도 로직을 구현
                if (response.status === 504 && retryCount < maxRetries) {
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    return makeRequest(value, retryCount + 1);
                }

                const data = await response.json();
                processedCount++;
                
                // 진행률 업데이트 표시
                const progressText = document.getElementById('progress-text');
                if (progressText) {
                    const percent = ((processedCount / totalCount) * 100).toFixed(1);
                    progressText.textContent = `처리 중... (${percent}%)`;
                }

                return { response, data, value };
            } catch (error) {
                if (error.message === 'AUTH_ERROR') {
                    throw error;
                }
                // 에러 발생 시 재시도
                if (retryCount < maxRetries) {
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    return makeRequest(value, retryCount + 1);
                }
                return { error, value };
            }
        }

        // 요청을 작은 그룹으로 나누어 순차적으로 처리 (서버 부하 분산)
        const chunkSize = 2; // 한 번에 처리할 요청 수
        for (let i = 0; i < values.length; i += chunkSize) {
            const chunk = values.slice(i, i + chunkSize);
            const chunkPromises = chunk.map(value => makeRequest(value)); // 각 요청을 별도의 Promise로 만듦

            try {
                const chunkResults = await Promise.all(chunkPromises); // Promise.all()을 사용하여 여러 요청을 동시에 처리
                
                // 각 요청의 결과 처리
                chunkResults.forEach(result => {
                    if (result.error) {
                        errors.push(`${result.value.tag}: 요청 처리 중 오류 발생`);
                    } else {
                        const { response, data, value } = result; // 요청 결과 처리
                        if (response.ok) {
                            results.push(value);
                            successfulTags.add(value.tag);
                            console.log(`성공한 요청: 환경: ${value.env}, 태그: ${value.tag}, ${containerId === 'stop-textbox-container' ? '시간: ' + value.time + ', ' : ''}동작: ${value.action}`);
                        } else {
                            errors.push(`${value.tag}: ${data.message || '요청 실패'}`);
                        }
                    }
                });

                // 다음 청크 처리 전 잠시 대기 (서버 부하 방지)
                if (i + chunkSize < values.length) { // 각 청크 처리 사이에 지연을 추가
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
            } catch (error) {
                // 인증 오류 처리
                if (error.message === 'AUTH_ERROR') {
                    loadingOverlay.classList.remove('active');
                    alert('인증이 만료되었습니다. 다시 로그인해주세요.');
                    window.location.replace('/');
                    return;
                }
            }
        }

        // 완료 후 로딩 오버레이 제거
        loadingOverlay.classList.remove('active');

        // 완료 후 최종 결과 메시지를 클라이언트에 반환
        let message = '';
        if (results.length > 0) {
            message += '성공적으로 처리된 요청:\n' + results.map(v =>
                containerId === 'stop-textbox-container'
                    ? `환경: ${v.env}\n태그: ${v.tag}\n시간: ${v.time}\n동작: ${v.action}`
                    : `환경: ${v.env}\n태그: ${v.tag}\n동작: ${v.action}`
            ).join('\n\n');
        }
        
        if (errors.length > 0) {
            if (message) message += '\n\n';
            message += '실패한 요청:\n' + errors.join('\n');
        }

        // 결과 알림
        alert(message);

        // 성공한 요청이 있으면 입력 필드 초기화
        if (results.length > 0) {
            container.innerHTML = '';
            updateDoneButtonForContainer(containerId);
        }

    } catch (error) {
        console.error('에러 발생:', error);
        loadingOverlay.classList.remove('active');
        alert('요청 처리 중 오류가 발생했습니다.');
    }
}
