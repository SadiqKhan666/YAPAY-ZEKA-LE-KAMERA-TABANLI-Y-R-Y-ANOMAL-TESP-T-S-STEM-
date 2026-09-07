"""Run a test that logs in as default doctor and downloads the PDF report for patient 1."""
from flask_server import app

def run():
    with app.test_client() as c:
        # login
        resp = c.post('/login', data={'username':'doctor', 'password':'1234'}, follow_redirects=True)
        print('Login status:', resp.status_code)
        # request report for patient 1
        r = c.get('/report/1')
        print('Report request status:', r.status_code, 'mimetype:', r.mimetype)
        if r.status_code == 200 and r.mimetype == 'application/pdf':
            with open('report_1_downloaded.pdf', 'wb') as f:
                f.write(r.data)
            print('Saved report_1_downloaded.pdf')
        else:
            print('Failed to get PDF. Response length:', len(r.data))

if __name__ == '__main__':
    run()
