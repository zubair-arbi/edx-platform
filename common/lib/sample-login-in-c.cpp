// cURL Test.cpp : Defines the entry point for the console application.
//

#include "stdafx.h"
#include <curl.h>
#include <xstring>



static std::string csrf;

static
size_t
header_callback(void * ptr, size_t size, size_t nmemb, void * fetcher_ptr) {
	std::string s;
	s.append(static_cast< char * >(ptr), size * nmemb);
	if (s.find("Set-Cookie: csrftoken=") == 0) {
			int start = s.find("=") + 1;
			int end = s.find(";");
			csrf = s.substr(start,end - start);
	}
	return size * nmemb;
}

int _tmain(int argc, _TCHAR* argv[])
{
	CURLcode code;
	curl_httppost * post	= NULL;
	curl_httppost * last	= NULL;
	curl_slist *headers = NULL;
	CURL * curl;
	curl = curl_easy_init();
	std::string url = "https://www.edx.org/login";
	curl_easy_reset(curl);			


	// First perform a get on the URL so that the CSRF token cookie can be retrieved
	// !!! Do not try to post the logon information without the CSRF token.  It will fail with a 403 and won't return
	// !!! the CSRF token in the failure.
	curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
	curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0);
	curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0);
	curl_easy_setopt(curl, CURLOPT_COOKIEJAR, "cookie");
	curl_easy_setopt(curl, CURLOPT_HEADERFUNCTION, header_callback);
	curl_easy_setopt(curl, CURLOPT_HTTPGET, NULL);

	// Set the headers
	headers = curl_slist_append(headers, "Expect:");
	headers = curl_slist_append(headers, "Referer:https://www.edx.org/");
	curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);			

	// Actually execute the get.
	code = curl_easy_perform(curl);

	curl_slist_free_all(headers);
	headers = NULL;

	// Now actually post the logon information with the CSRF token

	// remove the header parsing function
	curl_easy_setopt(curl, CURLOPT_HEADERFUNCTION, NULL);

	// Set the headers
	std::string csrf_header = "X-CSRFToken: ";
	csrf_header += csrf;
	headers = curl_slist_append(headers, csrf_header.c_str());
	headers = curl_slist_append(headers, "Expect:");
	headers = curl_slist_append(headers, "Referer:https://www.edx.org/");
	curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);			

	// add the logon to the URL path
	curl_easy_setopt(curl, CURLOPT_URL, url.c_str());

	// add the logon information
	curl_formadd(&post, &last, CURLFORM_COPYNAME, "email", CURLFORM_COPYCONTENTS, "ric_gray_junk@live.com", CURLFORM_END);
	curl_formadd(&post, &last, CURLFORM_COPYNAME, "password", CURLFORM_COPYCONTENTS, "Rewq$321", CURLFORM_END);
	curl_easy_setopt(curl, CURLOPT_HTTPPOST, post);

	// Actually performa 
	code = curl_easy_perform(curl);

	return 0;
}

