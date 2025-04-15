function updateTimes() {
    const now = new Date(); // 현재 시간 가져오기
    
    const utcString = now.toISOString().split('T')[1].split('.')[0]; // UTC 시간 문자열 가져오기
    document.getElementById('utc-time').textContent = utcString; // UTC 시간 표시
    
    const kstTime = new Date(now.getTime() + (9 * 60 * 60 * 1000)); // KST 시간 계산
    const kstString = kstTime.toISOString().split('T')[1].split('.')[0]; // KST 시간 문자열 가져오기    
    document.getElementById('kst-time').textContent = kstString; // KST 시간 표시
}

// 페이지 로드 시 즉시 시간 업데이트
updateTimes();

// 1초마다 시간 업데이트
setInterval(updateTimes, 1000);