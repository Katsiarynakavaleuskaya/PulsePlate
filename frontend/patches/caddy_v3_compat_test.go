// Synthetic compatibility witnesses for Caddy's selected smallstep v3 consumer.
package compat

import (
	"bytes"
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	v3 "github.com/go-jose/go-jose/v3"
	step "go.step.sm/crypto/jose"
)

func marshal(t *testing.T, value interface{}) []byte {
	t.Helper()
	encoded, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return encoded
}

func verifyRoundTrip(t *testing.T, private crypto.Signer, algorithm step.SignatureAlgorithm, wrong crypto.PublicKey) {
	t.Helper()
	switch expected := private.Public().(type) {
	case *rsa.PublicKey:
		other, ok := wrong.(*rsa.PublicKey)
		if !ok || other.N.BitLen() != expected.N.BitLen() || other.N.Cmp(expected.N) == 0 {
			t.Fatal("RSA negative control requires an independent RSA key of the same size")
		}
	case *ecdsa.PublicKey:
		other, ok := wrong.(*ecdsa.PublicKey)
		if !ok || other.Curve != expected.Curve || other.Equal(expected) {
			t.Fatal("EC negative control requires an independent key on the same curve")
		}
	default:
		t.Fatal("unsupported compatibility key type")
	}
	publicJWK := step.JSONWebKey{Key: private.Public()}
	opts := new(step.SignerOptions).WithHeader(step.HeaderKey("jwk"), publicJWK)
	signer, err := step.NewSigner(step.SigningKey{Algorithm: algorithm, Key: private}, opts)
	if err != nil {
		t.Fatal(err)
	}
	payload := []byte("synthetic-caddy-v3-compatibility")
	signed, err := signer.Sign(payload)
	if err != nil {
		t.Fatal(err)
	}
	compact, err := signed.CompactSerialize()
	if err != nil {
		t.Fatal(err)
	}
	for _, wire := range []string{compact, signed.FullSerialize()} {
		parsed, err := step.ParseJWS(wire)
		if err != nil {
			t.Fatal(err)
		}
		got, err := parsed.Verify(private.Public())
		if err != nil || !bytes.Equal(got, payload) {
			t.Fatalf("verified payload mismatch: %v", err)
		}
		if _, err := parsed.Verify(wrong); err == nil {
			t.Fatal("wrong verification key accepted")
		}
	}
}

func TestCaddySmallstepPublicAndPrivateKeys(t *testing.T) {
	wrong, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	for _, bits := range []int{2048, 4096} {
		t.Run(fmt.Sprintf("RSA%d", bits), func(t *testing.T) {
			key, err := rsa.GenerateKey(rand.Reader, bits)
			if err != nil {
				t.Fatal(err)
			}
			wrongRSA, err := rsa.GenerateKey(rand.Reader, bits)
			if err != nil {
				t.Fatal(err)
			}
			verifyRoundTrip(t, key, step.RS256, wrongRSA.Public())
			private := step.JSONWebKey{Key: key}
			public := step.JSONWebKey{Key: key.Public()}
			var keySet step.JSONWebKeySet
			if err := json.Unmarshal(marshal(t, map[string]interface{}{"keys": []step.JSONWebKey{private}}), &keySet); err != nil {
				t.Fatal(err)
			}
			if len(keySet.Keys) != 1 {
				t.Fatal("private JWKSet cardinality changed")
			}
			setKey, ok := keySet.Keys[0].Key.(*rsa.PrivateKey)
			if !ok {
				t.Fatalf("private JWKSet type lost: %T", keySet.Keys[0].Key)
			}
			verifyRoundTrip(t, setKey, step.RS256, wrongRSA.Public())
			password := []byte("synthetic-test-password-only")
			encrypted, err := step.EncryptJWK(&private, password)
			if err != nil {
				t.Fatal(err)
			}
			wire, err := encrypted.CompactSerialize()
			if err != nil {
				t.Fatal(err)
			}
			for _, tc := range []struct {
				name      string
				data      []byte
				isPrivate bool
			}{
				{"public", marshal(t, public), false},
				{"private", marshal(t, private), true},
				{"encrypted-private", []byte(wire), true},
			} {
				t.Run(tc.name, func(t *testing.T) {
					parsed, err := step.ParseKey(tc.data, step.WithPassword(password))
					if err != nil {
						t.Fatal(err)
					}
					want, err := public.Thumbprint(crypto.SHA256)
					if err != nil {
						t.Fatal(err)
					}
					got, err := parsed.Thumbprint(crypto.SHA256)
					if err != nil || !bytes.Equal(want, got) {
						t.Fatalf("key fingerprint mismatch: %v", err)
					}
					if tc.isPrivate {
						actual, ok := parsed.Key.(*rsa.PrivateKey)
						if !ok {
							t.Fatalf("private type lost: %T", parsed.Key)
						}
						verifyRoundTrip(t, actual, step.RS256, wrongRSA.Public())
					} else if _, ok := parsed.Key.(*rsa.PublicKey); !ok {
						t.Fatalf("public type lost: %T", parsed.Key)
					}
				})
			}
		})
	}
	key, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	verifyRoundTrip(t, key, step.ES256, wrong.Public())
}

func TestCaddySmallstepEmbeddedMaterial(t *testing.T) {
	for _, field := range []string{"k", "d", "p", "q", "dp", "dq", "qi"} {
		t.Run(field, func(t *testing.T) {
			key := map[string]interface{}{"kty": "RSA", "n": "AQAB", "e": "AQAB", field: "cHJpdmF0ZS1tYXJrZXI"}
			protected := base64.RawURLEncoding.EncodeToString(marshal(t, map[string]interface{}{"alg": "RS256", "jwk": key}))
			for _, wire := range []string{
				protected + ".dGVzdA.dGVzdA",
				`{"payload":"dGVzdA","protected":"` + protected + `","signature":"dGVzdA"}`,
				`{"payload":"dGVzdA","signatures":[{"protected":"` + protected + `","signature":"dGVzdA"}]}`,
			} {
				_, err := step.ParseJWS(wire)
				if err == nil || !strings.Contains(err.Error(), "JWK contains private parameters") || strings.Contains(err.Error(), "cHJpdmF0ZS1tYXJrZXI") {
					t.Fatalf("embedded material not rejected safely: %v", err)
				}
			}
		})
	}
	protected := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"RS256"}`))
	first := `{"protected":"` + protected + `","signature":"dGVzdA"}`
	second := `{"protected":"` + protected + `","header":{"kid":"second"},"signature":"dGVzdA"}`
	wire := `{"payload":"dGVzdA","signatures":[` + first + `,` + second + `]}`
	parsed, err := step.ParseJWS(wire)
	if err != nil || len(parsed.Signatures) != 2 {
		t.Fatalf("multi-signature parser contract: %v", err)
	}
	if parsed.Signatures[1].Header.KeyID != "second" || parsed.Signatures[1].Unprotected.KeyID != "second" {
		t.Fatal("unprotected header lost")
	}
	wire = strings.Replace(wire, `"kid":"second"`, `"jwk":{"kty":"oct","k":"c2VjcmV0"}`, 1)
	if _, err := step.ParseJWS(wire); err == nil || !strings.Contains(err.Error(), "JWK contains private parameters") {
		t.Fatalf("later embedded private key accepted: %v", err)
	}
}

func TestCaddySmallstepDecryptPassthroughIsNotKeyAcceptance(t *testing.T) {
	malformed := []byte(`{"protected":"invalid!","ciphertext":"dGVzdA"}`)
	if _, err := step.ParseEncrypted(string(malformed)); err == nil {
		t.Fatal("malformed JWE parsed")
	}
	got, err := step.Decrypt(malformed, step.WithPassword([]byte("synthetic-test-password-only")))
	if err != nil || !bytes.Equal(got, malformed) {
		t.Fatalf("existing Decrypt passthrough changed: %v", err)
	}
	if _, err := step.ParseKey(malformed); err == nil {
		t.Fatal("malformed JWE became a usable key")
	}
}

func TestCaddySmallstepJWTBuilderAndAudience(t *testing.T) {
	key := bytes.Repeat([]byte{0x42}, sha256.Size)
	signer, err := step.NewSigner(step.SigningKey{Algorithm: step.HS256, Key: key}, nil)
	if err != nil {
		t.Fatal(err)
	}
	wire, err := step.Signed(signer).Claims(step.Claims{Issuer: "synthetic", Audience: step.Audience{"one", "two"}}).CompactSerialize()
	if err != nil {
		t.Fatal(err)
	}
	parsed, err := step.ParseSigned(wire)
	if err != nil {
		t.Fatal(err)
	}
	var claims step.Claims
	if err := step.Verify(parsed, key, &claims); err != nil {
		t.Fatal(err)
	}
	if err := claims.Validate(step.Expected{Issuer: "synthetic", Audience: step.Audience{"one", "two"}}); err != nil {
		t.Fatal(err)
	}
	if err := claims.Validate(step.Expected{Audience: step.Audience{"one", "missing"}}); err == nil {
		t.Fatal("v3 all-audiences contract weakened")
	}
	// Retain explicit v3 type identity: the wrapper must not migrate to v4.
	var direct *v3.JSONWebSignature
	direct, err = step.ParseJWS(wire)
	if err != nil || direct == nil {
		t.Fatalf("v3 identity lost: %v", err)
	}
}
