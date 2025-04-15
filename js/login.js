const loginApiUrl = 'https://your-domain.com/api/login';


document.addEventListener('DOMContentLoaded', () => { // HTML 문서가 모두 로드된 후에 안쪽 코드를 실행하라는 의미
    const loginForm = document.getElementById("login-form"); // <form id="login-form"> 요소를 가져옴
    const loginErrorMsg = document.getElementById("login-error-msg"); // <p id="login-error-msg"> 요소를 가져옴

    // 페이지 로드 시 HTML 표시
    document.documentElement.style.display = "block";

    loginForm.addEventListener("submit", async (e) => { // 로그인 버튼을 클릭하면 아래의 함수를 실행
        e.preventDefault(); // 페이지 새로고침 방지 해당 함수 없으면 페이지 새로고침 됨

        const id = document.getElementById("id-field").value; // <input id="id-field"> 요소의 값을 가져옴
        const password = document.getElementById("password-field").value; // <input id="password-field"> 요소의 값을 가져옴

        try {
            // 로그인 API 호출
            const response = await fetch(loginApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',  // 쿠키를 주고받기 위해 필요
                body: JSON.stringify({
                    id: id,
                    password: password
                })
            });

            const data = await response.json();
            console.log('서버 응답 데이터:', data);  // 응답 데이터 콘솔에 출력
            console.log('응답 상태:', response.status);  // HTTP 상태 코드도 함께 출력
            console.log('응답 헤더:', [...response.headers.entries()]);  // 응답 헤더 확인
            console.log('로그인 후 쿠키:', document.cookie);  // 로그인 후 쿠키 상태 확인

            if (response.ok) {
                // 로그인 성공
                loginErrorMsg.style.opacity = 0;
                window.location.replace('/pages/main');
            } else {
                // 로그인 실패
                loginErrorMsg.style.opacity = 1;
                loginForm.reset();
            }
        } catch (error) {
            console.error('로그인 요청 중 오류 발생:', error);
            console.log('에러 상세 정보:', error.message);  // 에러 상세 정보 출력
            loginErrorMsg.textContent = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
            loginErrorMsg.style.opacity = 1;
        }
    });
});
