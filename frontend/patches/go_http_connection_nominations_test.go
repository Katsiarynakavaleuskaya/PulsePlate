// PulsePlate-maintained regression witnesses for the source-local Go 1.26.10
// Connection-nomination correction. Finite cases, not universal HTTP validation.
package http

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"io"
	"net"
	"net/http/internal/ascii"
	"net/textproto"
	"reflect"
	"strings"
	"testing"
	"time"
)

func ppHTTPReadBody(t *testing.T, raw, method string) (*Response, string, error) {
	t.Helper()
	resp, err := ReadResponse(bufio.NewReader(strings.NewReader(raw)), &Request{Method: method})
	if err != nil {
		t.Fatalf("PP_SETUP_READ: %v", err)
	}
	body, readErr := io.ReadAll(resp.Body)
	if err := resp.Body.Close(); err != nil {
		t.Fatalf("PP_BODY_CLOSE: %v", err)
	}
	return resp, string(body), readErr
}

func ppHTTPFixed(values []string) string {
	var wire strings.Builder
	wire.WriteString("HTTP/1.1 200 OK\r\nContent-Length: 1\r\n")
	for _, value := range values {
		wire.WriteString("Connection: " + value + "\r\n")
	}
	wire.WriteString("X-A: one\r\nX-B: two\r\n\r\nx")
	return wire.String()
}

// Unpatched baseline selection runs ONLY this regression, separately from
// passing controls. Its sole permitted failure is the final nomination check.
func TestPPHTTPConnectionBaseline(t *testing.T) {
	resp, body, err := ppHTTPReadBody(t, ppHTTPFixed([]string{"close, X-A, X-B"}), "GET")
	if err != nil || body != "x" || !resp.Close || resp.ContentLength != 1 ||
		len(resp.TransferEncoding) != 0 || len(resp.Trailer) != 0 ||
		resp.Header.Get("X-A") != "one" || resp.Header.Get("X-B") != "two" {
		t.Fatalf("PP_BASELINE_SETUP_OR_BODY_CLOSE_FAILURE: body=%q err=%v response=%+v", body, err, resp)
	}
	t.Log("PP_BASELINE_SETUP_BODY_CLOSE_OK")
	if got, want := resp.Header["Connection"], []string{"X-A", "X-B"}; !reflect.DeepEqual(got, want) {
		t.Errorf("PP_EXPECTED_NOMINATION_MISMATCH: got=%q want=%q", got, want)
	}
}

func TestPPHTTPConnectionSurvivors(t *testing.T) {
	cases := []struct {
		name   string
		values []string
		want   []string
	}{
		{"close_only", []string{"close"}, nil},
		{"repeated_close", []string{"CLOSE, close", "ClOsE"}, nil},
		{"first", []string{"close, X-A, X-B"}, []string{"X-A", "X-B"}},
		{"middle", []string{"X-A, close, X-B"}, []string{"X-A", "X-B"}},
		{"last", []string{"X-A, X-B, close"}, []string{"X-A", "X-B"}},
		{"separate_fields", []string{"X-A", "cLoSe", "X-B"}, []string{"X-A", "X-B"}},
		{"duplicates_and_spelling", []string{"close, X-A, x-a", "X-A, X-B"}, []string{"X-A", "x-a", "X-A", "X-B"}},
		{"ows_empty", []string{",\tclose , , X-A\t, ", "\tX-B ,"}, []string{"X-A", "X-B"}},
		{"opaque_near_misses", []string{"close, closex, \"close\", close;parameter, cloſe"}, []string{"closex", "\"close\"", "close;parameter", "cloſe"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body, err := ppHTTPReadBody(t, ppHTTPFixed(tc.values), "GET")
			if err != nil || body != "x" || !resp.Close || resp.ContentLength != 1 ||
				len(resp.TransferEncoding) != 0 || len(resp.Trailer) != 0 {
				t.Fatalf("framing/close changed: body=%q err=%v response=%+v", body, err, resp)
			}
			if !reflect.DeepEqual(resp.Header["Connection"], tc.want) {
				t.Errorf("Connection=%q want=%q", resp.Header["Connection"], tc.want)
			}
			if resp.Header.Get("X-A") != "one" || resp.Header.Get("X-B") != "two" {
				t.Fatal("parser deleted nominated actual fields")
			}
		})
	}
}

func TestPPHTTPConnectionFieldNameCase(t *testing.T) {
	wire := "HTTP/1.1 200 OK\r\nContent-Length: 1\r\n" +
		"cOnNeCtIoN: X-A\r\nCONNECTION: close\r\nConnection: X-B\r\n\r\nx"
	resp, body, err := ppHTTPReadBody(t, wire, "GET")
	if err != nil || body != "x" || !resp.Close || resp.ContentLength != 1 ||
		!reflect.DeepEqual(resp.Header["Connection"], []string{"X-A", "X-B"}) {
		t.Fatal("case-varied repeated field lost a nomination or changed framing")
	}
}

func TestPPHTTPBoundaryControls(t *testing.T) {
	cases := []struct {
		name   string
		values []string
	}{
		{"no_connection", nil},
		{"upgrade_no_close", []string{"Upgrade, X-A", "X-B"}},
		{"empty_elements_no_close", []string{", ,"}},
		{"near_misses_no_close", []string{"closex, \"close\", close;parameter, cloſe"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body, err := ppHTTPReadBody(t, ppHTTPFixed(tc.values), "GET")
			if err != nil || body != "x" || resp.Close || !reflect.DeepEqual(resp.Header["Connection"], tc.values) {
				t.Fatalf("no-close branch changed: body=%q err=%v response=%+v", body, err, resp)
			}
		})
	}
	t.Run("http10_close", func(t *testing.T) {
		wire := strings.Replace(ppHTTPFixed([]string{"close, X-A"}), "HTTP/1.1", "HTTP/1.0", 1)
		resp, body, err := ppHTTPReadBody(t, wire, "GET")
		if err != nil || body != "x" || !resp.Close ||
			!reflect.DeepEqual(resp.Header["Connection"], []string{"close, X-A"}) {
			t.Fatal("HTTP/1.0 early return changed")
		}
	})
	t.Run("http10_keepalive", func(t *testing.T) {
		wire := strings.Replace(ppHTTPFixed([]string{"keep-alive, X-A"}), "HTTP/1.1", "HTTP/1.0", 1)
		resp, body, err := ppHTTPReadBody(t, wire, "GET")
		if err != nil || body != "x" || resp.Close ||
			!reflect.DeepEqual(resp.Header["Connection"], []string{"keep-alive, X-A"}) {
			t.Fatal("HTTP/1.0 keepalive branch changed")
		}
	})
	t.Run("http10_close_keepalive", func(t *testing.T) {
		wire := strings.Replace(ppHTTPFixed([]string{"keep-alive, close, X-A"}), "HTTP/1.1", "HTTP/1.0", 1)
		resp, body, err := ppHTTPReadBody(t, wire, "GET")
		if err != nil || body != "x" || !resp.Close ||
			!reflect.DeepEqual(resp.Header["Connection"], []string{"keep-alive, close, X-A"}) {
			t.Fatal("HTTP/1.0 combined close/keepalive branch changed")
		}
	})
	t.Run("request_false_flag", func(t *testing.T) {
		req, err := ReadRequest(bufio.NewReader(strings.NewReader(
			"GET / HTTP/1.1\r\nHost: example.invalid\r\nConnection: close, X-A\r\nX-A: one\r\n\r\n")))
		if err != nil {
			t.Fatal(err)
		}
		defer req.Body.Close()
		if !req.Close || !reflect.DeepEqual(req.Header["Connection"], []string{"close, X-A"}) ||
			req.Header.Get("X-A") != "one" {
			t.Fatal("request header/close branch changed")
		}
	})
}

func TestPPHTTPFramingControls(t *testing.T) {
	t.Run("content_length_nomination", func(t *testing.T) {
		resp, body, err := ppHTTPReadBody(t, ppHTTPFixed([]string{"close, Content-Length, X-A"}), "GET")
		if err != nil || body != "x" || resp.ContentLength != 1 ||
			resp.Header.Get("Content-Length") != "1" || !resp.Close {
			t.Fatal("Content-Length nomination changed framing or actual field")
		}
		if !reflect.DeepEqual(resp.Header["Connection"], []string{"Content-Length", "X-A"}) {
			t.Fatal("Content-Length nomination lost")
		}
	})
	t.Run("chunked_trailer", func(t *testing.T) {
		wire := "HTTP/1.1 200 OK\r\nConnection: close, Transfer-Encoding, Trailer, X-A\r\n" +
			"Transfer-Encoding: chunked\r\nTrailer: X-Trailer\r\nX-A: one\r\n\r\n" +
			"3\r\nabc\r\n0\r\nX-Trailer: done\r\n\r\n"
		resp, body, err := ppHTTPReadBody(t, wire, "GET")
		if err != nil || body != "abc" || !resp.Close || resp.ContentLength != -1 ||
			!reflect.DeepEqual(resp.TransferEncoding, []string{"chunked"}) ||
			resp.Trailer.Get("X-Trailer") != "done" || resp.Header.Get("X-A") != "one" {
			t.Fatalf("chunked/trailer changed: body=%q err=%v response=%+v", body, err, resp)
		}
		if !reflect.DeepEqual(resp.Header["Connection"], []string{"Transfer-Encoding", "Trailer", "X-A"}) {
			t.Fatal("framing nominations lost")
		}
	})
	t.Run("eof_delimited", func(t *testing.T) {
		resp, body, err := ppHTTPReadBody(t, "HTTP/1.1 200 OK\r\nConnection: close, X-A\r\n\r\nabc", "GET")
		if err != nil || body != "abc" || !resp.Close || resp.ContentLength != -1 {
			t.Fatal("EOF-delimited framing changed")
		}
	})
	t.Run("truncated_content_length", func(t *testing.T) {
		resp, body, err := ppHTTPReadBody(t,
			"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nConnection: close, X-A\r\n\r\nabc", "GET")
		if err != io.ErrUnexpectedEOF || body != "abc" || !resp.Close || resp.ContentLength != 5 {
			t.Fatalf("truncated semantics changed: body=%q err=%v response=%+v", body, err, resp)
		}
	})
	for _, tc := range []struct {
		name, status, method string
	}{
		{"head", "200 OK", "HEAD"},
		{"no_content", "204 No Content", "GET"},
		{"not_modified", "304 Not Modified", "GET"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			resp, body, err := ppHTTPReadBody(t, "HTTP/1.1 "+tc.status+
				"\r\nConnection: close, X-A\r\n\r\n", tc.method)
			if err != nil || body != "" || !resp.Close {
				t.Fatal("no-body semantics changed")
			}
		})
	}
}

func TestPPHTTPMalformedReaderControls(t *testing.T) {
	cases := []struct{ name, wire string }{
		{"embedded_cr", "HTTP/1.1 200 OK\r\nConnection: close, X-A\rX-B\r\nContent-Length: 0\r\n\r\n"},
		{"nul_value", "HTTP/1.1 200 OK\r\nConnection: close, X-A\x00\r\nContent-Length: 0\r\n\r\n"},
		{"invalid_field_name", "HTTP/1.1 200 OK\r\nBad[Header: x\r\nContent-Length: 0\r\n\r\n"},
		{"bare_lf_broken_field", "HTTP/1.1 200 OK\r\nConnection: close,\nnot-a-header\r\n\r\n"},
		{"invalid_content_length", "HTTP/1.1 200 OK\r\nConnection: close, X-A\r\nContent-Length: nope\r\n\r\n"},
		{"invalid_transfer_coding", "HTTP/1.1 200 OK\r\nConnection: close, X-A\r\nTransfer-Encoding: bogus\r\n\r\n"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, err := ReadResponse(bufio.NewReader(strings.NewReader(tc.wire)), &Request{Method: "GET"})
			if err == nil {
				resp.Body.Close()
				t.Fatal("malformed reader input unexpectedly accepted")
			}
			t.Logf("PP_READER_REJECT name=%s error=%T:%v", tc.name, err, err)
		})
	}
}

// Native reader acceptance is distinct from valid Connection-token grammar.
// The two runs compare these body/close observations, retaining raw Header logs.
func TestPPHTTPMalformedAcceptedParity(t *testing.T) {
	t.Run("legacy_space_field_name", func(t *testing.T) {
		// Preserve the exact input accepted by the unpatched native reader.
		wire := "HTTP/1.1 200 OK\r\nBad Header: x\r\nContent-Length: 0\r\n\r\n"
		resp, body, err := ppHTTPReadBody(t, wire, "GET")
		want := Header{"Bad Header": {"x"}, "Content-Length": {"0"}}
		if err != nil || body != "" || resp.Close || resp.ContentLength != 0 ||
			len(resp.TransferEncoding) != 0 || len(resp.Trailer) != 0 ||
			!reflect.DeepEqual(resp.Header, want) {
			t.Fatalf("legacy space-name acceptance changed: body=%q err=%v response=%+v", body, err, resp)
		}
		t.Logf("PP_ACCEPTED_PARITY name=legacy_space_field_name close=%v length=%d body=%q error=%v field=%q",
			resp.Close, resp.ContentLength, body, err, resp.Header["Bad Header"])
		t.Logf("PP_ACCEPTED_HEADER name=legacy_space_field_name values=%q", resp.Header["Connection"])
	})
	cases := []struct{ name, wire string }{
		{"opaque_obs_text", ppHTTPFixed([]string{"close, cloſe, \"close\", close;parameter"})},
		{"bare_lf_lines", strings.ReplaceAll(ppHTTPFixed([]string{"close, X-A"}), "\r\n", "\n")},
		{"folded_ows", "HTTP/1.1 200 OK\r\nContent-Length: 1\r\nConnection: close,\r\n\tX-A\r\n\r\nx"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body, err := ppHTTPReadBody(t, tc.wire, "GET")
			if err != nil || body != "x" || !resp.Close || resp.ContentLength != 1 {
				t.Fatalf("accepted-input framing parity failed: %q %v %+v", body, err, resp)
			}
			t.Logf("PP_ACCEPTED_PARITY name=%s close=%v length=%d body=%q error=%v",
				tc.name, resp.Close, resp.ContentLength, body, err)
			t.Logf("PP_ACCEPTED_HEADER name=%s values=%q", tc.name, resp.Header["Connection"])
		})
	}
}

func TestPPHTTPResponseWriteRoundTrip(t *testing.T) {
	resp, err := ReadResponse(bufio.NewReader(strings.NewReader(ppHTTPFixed([]string{"close, X-A, X-B"}))),
		&Request{Method: "GET"})
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var wire bytes.Buffer
	if err := resp.Write(&wire); err != nil {
		t.Fatal(err)
	}
	ppHTTPCheckSerializedConnection(t, wire.Bytes(), []string{"X-A", "X-B"})
	next, body, err := ppHTTPReadBody(t, wire.String(), "GET")
	if err != nil || body != "x" || !next.Close || next.ContentLength != 1 ||
		!reflect.DeepEqual(next.Header["Connection"], []string{"X-A", "X-B"}) ||
		next.Header.Get("X-A") != "one" || next.Header.Get("X-B") != "two" {
		t.Fatal("ReadResponse/Write changed body or lost nominations")
	}
}

func TestPPHTTPTransportCloseNominees(t *testing.T) {
	ppHTTPTransportCloseNominees(t, "close, X-A")
}

func TestPPHTTPTransportPersistenceOptions(t *testing.T) {
	ppHTTPTransportCloseNominees(t, "keep-alive, close, X-A")
}

func ppHTTPTransportCloseNominees(t *testing.T, connection string) {
	t.Helper()
	listener, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	if err := listener.(*net.TCPListener).SetDeadline(time.Now().Add(8 * time.Second)); err != nil {
		t.Fatal(err)
	}
	type observation struct {
		peers []string
		err   error
	}
	done := make(chan observation, 1)
	go func() {
		defer close(done)
		var seen []string
		for range 2 {
			conn, err := listener.Accept()
			if err != nil {
				done <- observation{seen, err}
				return
			}
			seen = append(seen, conn.RemoteAddr().String())
			if err := conn.SetDeadline(time.Now().Add(5 * time.Second)); err != nil {
				conn.Close()
				done <- observation{seen, err}
				return
			}
			reader := bufio.NewReader(conn)
			req, err := ReadRequest(reader)
			if err != nil {
				conn.Close()
				done <- observation{seen, err}
				return
			}
			req.Body.Close()
			_, err = io.WriteString(conn, "HTTP/1.1 200 OK\r\nContent-Length: 3\r\n"+
				"Connection: "+connection+"\r\nX-A: one\r\n\r\nabc")
			if err == nil {
				// Do not close server-side first: the real Transport must close.
				one := make([]byte, 1)
				_, err = reader.Read(one)
				if err == io.EOF {
					err = nil
				} else if err == nil {
					err = fmt.Errorf("connection reused before client close")
				}
			}
			conn.Close()
			if err != nil {
				done <- observation{seen, err}
				return
			}
		}
		done <- observation{peers: seen}
	}()
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()
	transport := &Transport{DialContext: (&net.Dialer{Timeout: 2 * time.Second}).DialContext}
	defer transport.CloseIdleConnections()
	t.Cleanup(func() {
		cancel()
		listener.Close()
		transport.CloseIdleConnections()
		select {
		case <-done:
		case <-time.After(6 * time.Second):
			t.Error("raw Transport server did not terminate")
		}
	})
	for range 2 {
		req, err := NewRequestWithContext(ctx, "GET", "http://"+listener.Addr().String()+"/", nil)
		if err != nil {
			t.Fatal(err)
		}
		resp, err := transport.RoundTrip(req)
		if err != nil {
			t.Fatal(err)
		}
		body, readErr := io.ReadAll(resp.Body)
		closeErr := resp.Body.Close()
		if readErr != nil || closeErr != nil || string(body) != "abc" || !resp.Close ||
			resp.ContentLength != 3 || resp.Header.Get("X-A") != "one" ||
			!reflect.DeepEqual(resp.Header["Connection"], []string{"X-A"}) {
			t.Fatalf("Transport response mismatch: body=%q read=%v close=%v response=%+v",
				body, readErr, closeErr, resp)
		}
	}
	select {
	case result := <-done:
		if result.err != nil || len(result.peers) != 2 || result.peers[0] == result.peers[1] {
			t.Fatalf("nonreuse proof failed: %+v", result)
		}
	case <-ctx.Done():
		t.Fatalf("nonreuse completion: %v", ctx.Err())
	}
}

func TestPPHTTPPersistenceOptions(t *testing.T) {
	cases := []struct {
		name   string
		values []string
		want   []string
	}{
		{"same_line", []string{"keep-alive, close"}, nil},
		{"reversed", []string{"close, keep-alive"}, nil},
		{"split_fields", []string{"keep-alive", "close"}, nil},
		{"case_duplicate_controls", []string{"KEEP-ALIVE, cLoSe", "keep-alive, CLOSE"}, nil},
		{"nominees", []string{"keep-alive, X-A, close, X-B"}, []string{"X-A", "X-B"}},
		{"duplicate_nominees", []string{"KEEP-ALIVE, X-A", "close, x-a", "X-B, keep-alive, X-A"}, []string{"X-A", "x-a", "X-B", "X-A"}},
		{"ows_empty", []string{",\tKEEP-ALIVE , , close, X-A\t,", ", X-B ,"}, []string{"X-A", "X-B"}},
		{"opaque_near_misses", []string{"close, keep-alive, keep-alivex, \"keep-alive\", keep-alive;timeout=5, keep‐alive"}, []string{"keep-alivex", "\"keep-alive\"", "keep-alive;timeout=5", "keep‐alive"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			wire := strings.Replace(ppHTTPFixed(tc.values), "X-A: one\r\n",
				"Keep-Alive: timeout=5\r\nX-A: one\r\n", 1)
			resp, body, err := ppHTTPReadBody(t, wire, "GET")
			if err != nil || body != "x" || !resp.Close || resp.ContentLength != 1 ||
				len(resp.TransferEncoding) != 0 || len(resp.Trailer) != 0 ||
				!reflect.DeepEqual(resp.Header["Connection"], tc.want) {
				t.Fatalf("persistence/nomination result differs: body=%q err=%v response=%+v", body, err, resp)
			}
			if resp.Header.Get("Keep-Alive") != "timeout=5" ||
				resp.Header.Get("X-A") != "one" || resp.Header.Get("X-B") != "two" {
				t.Fatal("parser deleted actual response fields")
			}
		})
	}
}

func TestPPHTTPPersistenceBoundaryControls(t *testing.T) {
	for _, tc := range []struct {
		name   string
		values []string
	}{
		{"keepalive_only", []string{"keep-alive"}},
		{"keepalive_with_nominees", []string{"keep-alive, X-A", "X-B"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			wire := strings.Replace(ppHTTPFixed(tc.values), "X-A: one\r\n",
				"Keep-Alive: timeout=5\r\nX-A: one\r\n", 1)
			resp, body, err := ppHTTPReadBody(t, wire, "GET")
			if err != nil || body != "x" || resp.Close || resp.ContentLength != 1 ||
				!reflect.DeepEqual(resp.Header["Connection"], tc.values) ||
				resp.Header.Get("Keep-Alive") != "timeout=5" {
				t.Fatal("no-close keep-alive response changed")
			}
			fresh, err := ReadResponse(bufio.NewReader(strings.NewReader(wire)), &Request{Method: "GET"})
			if err != nil {
				t.Fatal(err)
			}
			defer fresh.Body.Close()
			var serialized bytes.Buffer
			if err := fresh.Write(&serialized); err != nil {
				t.Fatal(err)
			}
			reader := textproto.NewReader(bufio.NewReader(bytes.NewReader(serialized.Bytes())))
			status, err := reader.ReadLine()
			if err != nil || status != "HTTP/1.1 200 OK" {
				t.Fatal("no-close serialized status changed")
			}
			headers, err := reader.ReadMIMEHeader()
			if err != nil || !reflect.DeepEqual(headers["Connection"], tc.values) ||
				headers.Get("Keep-Alive") != "timeout=5" {
				t.Fatal("no-close serialized Connection fields changed")
			}
			next, body, err := ppHTTPReadBody(t, serialized.String(), "GET")
			if err != nil || body != "x" || next.Close || next.ContentLength != 1 {
				t.Fatal("no-close serialization changed body/close/framing")
			}
		})
	}
	t.Run("eof_close_without_close_token", func(t *testing.T) {
		resp, body, err := ppHTTPReadBody(t, "HTTP/1.1 200 OK\r\n"+
			"Connection: keep-alive, X-A\r\nKeep-Alive: timeout=5\r\nX-A: one\r\n\r\nabc", "GET")
		if err != nil || body != "abc" || !resp.Close || resp.ContentLength != -1 ||
			!reflect.DeepEqual(resp.Header["Connection"], []string{"keep-alive, X-A"}) ||
			resp.Header.Get("Keep-Alive") != "timeout=5" || resp.Header.Get("X-A") != "one" {
			t.Fatal("EOF-derived close incorrectly entered explicit-close filtering")
		}
	})
	t.Run("request_both_controls", func(t *testing.T) {
		req, err := ReadRequest(bufio.NewReader(strings.NewReader(
			"GET / HTTP/1.1\r\nHost: example.invalid\r\nConnection: keep-alive, close, X-A\r\n" +
				"Keep-Alive: timeout=5\r\nX-A: one\r\n\r\n")))
		if err != nil {
			t.Fatal(err)
		}
		defer req.Body.Close()
		body, err := io.ReadAll(req.Body)
		if err != nil || len(body) != 0 || !req.Close ||
			!reflect.DeepEqual(req.Header["Connection"], []string{"keep-alive, close, X-A"}) ||
			req.Header.Get("Keep-Alive") != "timeout=5" || req.Header.Get("X-A") != "one" {
			t.Fatal("request persistence/header/body boundary changed")
		}
	})
}

// Inspect every serialized field using the native MIME reader, then every
// Connection option using the native list iterator and ASCII comparator.
func ppHTTPCheckSerializedConnection(t *testing.T, wire []byte, want []string) {
	t.Helper()
	reader := textproto.NewReader(bufio.NewReader(bytes.NewReader(wire)))
	status, err := reader.ReadLine()
	if err != nil || status != "HTTP/1.1 200 OK" {
		t.Fatalf("serialized status: %q %v", status, err)
	}
	headers, err := reader.ReadMIMEHeader()
	if err != nil {
		t.Fatal(err)
	}
	closes := 0
	var survivors []string
	for _, value := range headers["Connection"] {
		foreachHeaderElement(value, func(element string) {
			switch {
			case ascii.EqualFold(element, "close"):
				closes++
			case ascii.EqualFold(element, "keep-alive"):
				t.Error("serialized competing keep-alive Connection option")
			default:
				survivors = append(survivors, element)
			}
		})
	}
	if closes != 1 || !reflect.DeepEqual(survivors, want) {
		t.Fatalf("serialized Connection options: close=%d survivors=%q want=%q",
			closes, survivors, want)
	}
}

func TestPPHTTPPersistenceWriteRoundTrip(t *testing.T) {
	for _, tc := range []struct {
		name  string
		value string
		want  []string
	}{
		{"controls_only", "keep-alive, close", nil},
		{"controls_and_nominees", "keep-alive, X-A, close, X-B, X-A", []string{"X-A", "X-B", "X-A"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			input := strings.Replace(ppHTTPFixed([]string{tc.value}), "X-A: one\r\n",
				"Keep-Alive: timeout=5\r\nX-A: one\r\n", 1)
			resp, err := ReadResponse(bufio.NewReader(strings.NewReader(input)), &Request{Method: "GET"})
			if err != nil {
				t.Fatal(err)
			}
			defer resp.Body.Close()
			if !resp.Close || resp.ContentLength != 1 ||
				!reflect.DeepEqual(resp.Header["Connection"], tc.want) ||
				resp.Header.Get("Keep-Alive") != "timeout=5" {
				t.Fatal("initial parsed persistence state differs")
			}
			var wire bytes.Buffer
			if err := resp.Write(&wire); err != nil {
				t.Fatal(err)
			}
			ppHTTPCheckSerializedConnection(t, wire.Bytes(), tc.want)
			next, body, err := ppHTTPReadBody(t, wire.String(), "GET")
			if err != nil || body != "x" || !next.Close || next.ContentLength != 1 ||
				!reflect.DeepEqual(next.Header["Connection"], tc.want) ||
				next.Header.Get("Keep-Alive") != "timeout=5" ||
				next.Header.Get("X-A") != "one" || next.Header.Get("X-B") != "two" {
				t.Fatal("persistence roundtrip lost metadata/body or actual fields")
			}
		})
	}
}
