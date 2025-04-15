const logoutApiUrl = 'https://your-domain.com/api/logout';

document.getElementById('logout-button').addEventListener('click', async () => { // 로그아웃 버튼을 클릭하면 아래의 함수를 실행
    try {
        const response = await fetch(logoutApiUrl, {
            method: 'POST',
            credentials: 'include'  // 쿠키 포함하여 요청
        });

        const data = await response.json();
        console.log('서버 응답:', data);

        if (response.ok) {
            console.log('로그아웃 성공');
            // 클라이언트 쿠키 삭제 - domain 속성 포함
            document.cookie = 'token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=your-domain.com'; // 쿠키 삭제
            window.location.replace('/');
        } else {
            console.error('로그아웃 실패:', data.message);
        }
    } catch (error) {
        console.error('로그아웃 처리 중 오류 발생:', error);
    }
});
